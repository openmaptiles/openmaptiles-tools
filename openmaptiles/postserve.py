import logging
from functools import partial
from typing import Union

import asyncpg
import tornado.ioloop
import tornado.web
from asyncpg import Connection, ConnectionDoesNotExistError
from asyncpg.pool import Pool

from openmaptiles.consts import PIXEL_SCALE
from openmaptiles.language import languages_to_sql, language_codes_to_names
from openmaptiles.sqltomvt import MvtGenerator
from openmaptiles.tileset import Tileset


class RequestHandledWithCors(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'GET, OPTIONS')

    def options(self):
        self.set_status(204)
        self.finish()


class GetTile(RequestHandledWithCors):
    pool: Pool
    query: str
    verbose: bool
    connection: Union[Connection, None]
    cancelled: bool

    def initialize(self, pool, query, verbose):
        self.pool = pool
        self.query = query
        self.verbose = verbose
        self.connection = None
        self.cancelled = False

    async def get(self, zoom, x, y):
        self.set_header("Content-Type", "application/x-protobuf")
        self.set_header("Content-Disposition", "attachment")
        self.set_header("Access-Control-Allow-Origin", "*")
        try:
            async with self.pool.acquire() as connection:
                self.connection = connection
                query = self.query
                zoom, x, y = int(zoom), int(x), int(y)
                if self.verbose:
                    # Make it easier to track queries in pg_stat_activity table
                    query = f"/* {zoom}/{x}/{y} */ " + query
                tile = await connection.fetchval(query, zoom, x, y)
                if tile:
                    self.write(tile)
                else:
                    self.set_status(204)
                    if self.verbose:
                        print(f"Tile {zoom}/{x}/{y} is empty.")

        except ConnectionDoesNotExistError as err:
            if not self.cancelled:
                raise err
            elif self.verbose:
                print(f"Tile request {zoom}/{x}/{y} was cancelled.")
        finally:
            self.connection = None

    def on_connection_close(self):
        if self.connection:
            self.cancelled = True
            self.connection.terminate()


class GetMetadata(RequestHandledWithCors):
    metadata: str

    def initialize(self, metadata):
        self.metadata = metadata

    def get(self):
        self.write(self.metadata)
        print('Returning metadata')


class Postserve:
    known_types = dict(bool="Boolean", text="String", int4="Number", int8="Number")
    pool: Pool

    def __init__(self, host, port, pghost, pgport, dbname, user, password, metadata,
                 layers, tileset_path, sql_file, mask_layer, mask_zoom, verbose):
        self.host = host
        self.port = port
        self.pghost = pghost
        self.pgport = pgport
        self.dbname = dbname
        self.user = user
        self.password = password
        self.metadata = metadata
        self.layers = layers
        self.tileset_path = tileset_path
        self.sql_file = sql_file
        self.mask_layer = mask_layer
        self.mask_zoom = mask_zoom
        self.verbose = verbose

        self.tileset = Tileset.parse(self.tileset_path)

    async def generate_metadata(self):
        async with self.pool.acquire() as connection:
            # Get all Postgres types and keep those we know about
            types = await connection.fetch("select oid, typname from pg_type")
            pg_types = {row[0]: self.known_types[row[1]] for row in types
                        if row[1] in self.known_types}

            vector_layers = []
            for layer_def in self.tileset.layers:
                layer = layer_def["layer"]

                # Get field names and types by executing a dummy query
                query = layer['datasource']['query']
                if '{name_languages}' in query:
                    languages = self.tileset.definition.get('languages', [])
                else:
                    languages = False
                if languages:
                    query = query.format(name_languages=languages_to_sql(languages))
                query = (query
                         .replace("!bbox!", "TileBBox(0, 0, 0)")
                         .replace("z(!scale_denominator!)", "0")
                         .replace("!pixel_width!", str(PIXEL_SCALE))
                         .replace("!pixel_height!", str(PIXEL_SCALE)))
                st = await connection.prepare(
                    f"SELECT * FROM {query} WHERE false LIMIT 0")

                query_fields = {v.name for v in st.get_attributes()}
                layer_fields, geometry_field = layer_def.get_fields()
                if languages:
                    layer_fields += language_codes_to_names(languages)
                layer_fields = set(layer_fields)

                if geometry_field not in query_fields:
                    raise ValueError(f"Layer '{layer['id']}' query does not generate "
                                     f"expected 'geometry' field")
                query_fields.remove(geometry_field)

                if layer_fields != query_fields:
                    same = layer_fields.intersection(query_fields)
                    layer_fields -= same
                    query_fields -= same
                    error = f"Declared fields in layer '{layer['id']}' do not match " \
                            f"the fields received from a query:\n"
                    if layer_fields:
                        error += f"  These fields were declared, but not returned by " \
                                 f"the query: {', '.join(layer_fields)}"
                    if query_fields:
                        error += f"  These fields were returned by the query, " \
                                 f"but not declared: {', '.join(query_fields)}"
                    raise ValueError(error)

            fields = {fld.name: pg_types[fld.type.oid]
                      for fld in st.get_attributes() if fld.type.oid in pg_types}
            vector_layers.append(dict(
                id=layer["id"],
                fields=fields,
                maxzoom=self.metadata["maxzoom"],
                minzoom=self.metadata["minzoom"],
                description=layer["description"],
            ))

        self.metadata["vector_layers"] = vector_layers
        self.metadata["tiles"] = [
            f"http://{self.host}:{self.port}" + "/tiles/{z}/{x}/{y}.pbf",
        ]

    def serve(self):
        if self.sql_file:
            with open(self.sql_file) as stream:
                query = stream.read()
            print(f'Loaded {self.sql_file}')
        else:
            mvt = MvtGenerator(self.tileset, self.mask_layer, self.mask_zoom,
                               layer_ids=self.layers)
            query = mvt.generate_sqltomvt_query()

        if self.verbose:
            print(f'Using SQL query:\n\n-------\n\n{query}\n\n-------\n\n')

        tornado.log.access_log.setLevel(logging.INFO if self.verbose else logging.ERROR)

        dsn = f"postgresql://{self.user}:{self.password}@" \
              f"{self.pghost}:{self.pgport}/{self.dbname}"

        io_loop = tornado.ioloop.IOLoop.current()
        self.pool = io_loop.run_sync(partial(asyncpg.create_pool, dsn=dsn))
        io_loop.run_sync(partial(self.generate_metadata))

        application = tornado.web.Application([
            (
                r"/",
                GetMetadata,
                dict(metadata=self.metadata)
            ),
            (
                r"/tiles/([0-9]+)/([0-9]+)/([0-9]+).pbf",
                GetTile,
                dict(pool=self.pool, query=query, verbose=self.verbose)
            ),
        ])

        application.listen(self.port)
        print(f"Postserve started, listening on 0.0.0.0:{self.port}")
        print(f"Use http://{self.host}:{self.port} as the data source")
        tornado.ioloop.IOLoop.instance().start()
