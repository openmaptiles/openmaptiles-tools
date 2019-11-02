import logging
from functools import partial
from typing import Union

import asyncpg
import tornado.ioloop
import tornado.web
from asyncpg import Connection, ConnectionDoesNotExistError
from asyncpg.pool import Pool

from .sqltomvt import MvtGenerator
from .tileset import Tileset


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
    pool: Pool

    def __init__(self, host, port, pghost, pgport, dbname, user, password, metadata,
                 layers, tileset_path, sql_file, verbose):
        self.host = host
        self.port = port
        self.pghost = pghost
        self.pgport = pgport
        self.dbname = dbname
        self.user = user
        self.password = password
        self.metadata = metadata
        self.tileset_path = tileset_path
        self.sql_file = sql_file
        self.verbose = verbose

        self.tileset = Tileset.parse(self.tileset_path)
        self.mvt = MvtGenerator(self.tileset, layers)

    async def generate_metadata(self):
        self.metadata["tiles"] = [
            f"http://{self.host}:{self.port}" + "/tiles/{z}/{x}/{y}.pbf",
        ]
        self.metadata["vector_layers"] = []

        async with self.pool.acquire() as conn:
            pg_types = await get_sql_types(conn)
            for layer_id, layer_def in self.mvt.get_layers():
                fields = await self.mvt.validate_layer_fields(conn, layer_id, layer_def)
                unknown = {
                    name: oid for name, oid in fields.items()
                    if oid not in pg_types and name != 'geometry'
                }
                if unknown:
                    print(f"Ignoring fields with unknown SQL types (OIDs): "
                          f"[{', '.join([f'{n} ({o})' for n, o in unknown.items()])}]")

                self.metadata["vector_layers"].append(dict(
                    id=(layer_def["layer"]['id']),
                    fields={name: pg_types[type_oid]
                            for name, type_oid in fields.items()
                            if type_oid in pg_types},
                    maxzoom=self.metadata["maxzoom"],
                    minzoom=self.metadata["minzoom"],
                    description=layer_def["layer"]["description"],
                ))

    def serve(self):
        if self.sql_file:
            with open(self.sql_file) as stream:
                query = stream.read()
            print(f'Loaded {self.sql_file}')
        else:
            query = self.mvt.generate_sqltomvt_query()

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


async def get_sql_types(connection: Connection):
    """
    Get Postgres types that we can handle,
    and return the mapping of OSM type id (oid) => MVT style type
    """
    sql_to_mvt_types = dict(
        bool="Boolean",
        text="String",
        int4="Number",
        int8="Number",
    )
    types = await connection.fetch(
        "select oid, typname from pg_type where typname = ANY($1::text[])",
        list(sql_to_mvt_types.keys())
    )
    return {row['oid']: sql_to_mvt_types[row['typname']] for row in types}
