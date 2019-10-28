import logging
from functools import partial
from typing import Union

import asyncpg
import tornado.ioloop
import tornado.web
from asyncpg import Connection, ConnectionDoesNotExistError
from asyncpg.pool import Pool

from openmaptiles.consts import PIXEL_SCALE
from openmaptiles.language import languages_to_sql
from openmaptiles.sqltomvt import generate_sqltomvt_query
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
                tile = await connection.fetchval(self.query, int(zoom), int(x), int(y))
                self.write(tile)
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


async def generate_metadata(pool, tileset, host, port, metadata):
    async with pool.acquire() as connection:
        # Get all Postgres types and keep those we know about
        known_types = dict(bool="Boolean", text="String", int4="Number", int8="Number")
        types = await connection.fetch("select oid, typname from pg_type")
        pg_types = {row[0]: known_types[row[1]] for row in types if
                    row[1] in known_types}

        vector_layers = []
        for layer_def in tileset.layers:
            layer = layer_def["layer"]

            # Get field names and types by executing a dummy query
            langs = languages_to_sql(tileset.definition.get('languages', []))
            query = (layer['datasource']['query']
                     .format(name_languages=langs)
                     .replace("!bbox!", "TileBBox(0, 0, 0)")
                     .replace("z(!scale_denominator!)", "0")
                     .replace("!pixel_width!", str(PIXEL_SCALE))
                     .replace("!pixel_height!", str(PIXEL_SCALE)))
            st = await connection.prepare(f"SELECT * FROM {query} WHERE false LIMIT 0")
            fields = {fld.name: pg_types[fld.type.oid]
                      for fld in st.get_attributes() if fld.type.oid in pg_types}

            vector_layers.append(dict(
                id=layer["id"],
                fields=fields,
                maxzoom=metadata["maxzoom"],
                minzoom=metadata["minzoom"],
                description=layer["description"],
            ))

        metadata["vector_layers"] = vector_layers
        metadata["tiles"] = [f"http://{host}:{port}" + "/tiles/{z}/{x}/{y}.pbf"]


def serve(host, port, pghost, pgport, dbname, user, password, metadata, tileset_path,
          sql_file, mask_layer, mask_zoom, verbose):
    tileset = Tileset.parse(tileset_path)

    if sql_file:
        with open(sql_file) as stream:
            query = stream.read()
        print(f'Loaded {sql_file}')
    else:
        query = generate_sqltomvt_query({
            'tileset': tileset,
            'mask-layer': mask_layer,
            'mask-zoom': mask_zoom,
        })

    if verbose:
        print(f'Using SQL query:\n\n-------\n\n{query}\n\n-------\n\n')

    tornado.log.access_log.setLevel(logging.INFO if verbose else logging.ERROR)

    dsn = f"postgresql://{user}:{password}@{pghost}:{pgport}/{dbname}"

    io_loop = tornado.ioloop.IOLoop.current()
    pool = io_loop.run_sync(partial(asyncpg.create_pool, dsn=dsn))
    io_loop.run_sync(
        partial(generate_metadata, pool=pool, tileset=tileset, host=host, port=port,
                metadata=metadata))

    application = tornado.web.Application([
        (
            r"/",
            GetMetadata,
            dict(metadata=metadata)
        ),
        (
            r"/tiles/([0-9]+)/([0-9]+)/([0-9]+).pbf",
            GetTile,
            dict(pool=pool, query=query, verbose=verbose)
        ),
    ])

    application.listen(port)
    print(f"Postserve started, listening on 0.0.0.0:{port}")
    print(f"Use http://{host}:{port} as the data source")
    tornado.ioloop.IOLoop.instance().start()
