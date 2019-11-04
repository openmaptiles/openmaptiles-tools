import logging
from functools import partial
from typing import Union

import asyncpg
import tornado.ioloop
import tornado.web
from asyncpg import Connection, ConnectionDoesNotExistError
from asyncpg.pool import Pool

from openmaptiles.pgutils import show_settings
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
    key_column: str
    verbose: bool
    connection: Union[Connection, None]
    cancelled: bool

    def initialize(self, pool, query, key_column, verbose):
        self.pool = pool
        self.query = query
        self.key_column = key_column
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
                if self.key_column:
                    row = await connection.fetchrow(query, zoom, x, y)
                    tile = row['mvt']
                    key = row['key']
                else:
                    tile = await connection.fetchval(query, zoom, x, y)
                    key = None
                if tile:
                    self.write(tile)
                    if self.key_column:
                        print(f"Tile {zoom}/{x}/{y} key={key} is {len(tile):,} bytes")
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
    mvt: MvtGenerator

    def __init__(self, host, port, pghost, pgport, dbname, user, password, metadata,
                 layers, tileset_path, sql_file, key_column, disable_feature_ids,
                 gzip, verbose):
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
        self.layer_ids = layers
        self.key_column = key_column
        self.gzip = gzip
        self.disable_feature_ids = disable_feature_ids
        self.verbose = verbose

        self.tileset = Tileset.parse(self.tileset_path)

    async def init_connection(self):
        self.metadata["tiles"] = [
            f"http://{self.host}:{self.port}" + "/tiles/{z}/{x}/{y}.pbf",
        ]
        self.metadata["vector_layers"] = []

        async with self.pool.acquire() as conn:
            settings, use_feature_id = await show_settings(conn)
            if self.disable_feature_ids:
                use_feature_id = False
            self.mvt = MvtGenerator(self.tileset, layer_ids=self.layer_ids,
                                    key_column=self.key_column, gzip=self.gzip,
                                    use_feature_id=use_feature_id)
            pg_types = await get_sql_types(conn)
            for layer_id, layer_def in self.mvt.get_layers():
                fields = await self.mvt.validate_layer_fields(conn, layer_id, layer_def)
                unknown = {
                    name: oid for name, oid in fields.items()
                    if oid not in pg_types and name != layer_def.geometry_field
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
        tornado.log.access_log.setLevel(logging.INFO if self.verbose else logging.ERROR)

        print(f'Connecting to PostgreSQL at {self.pghost}:{self.pgport}, '
              f'db={self.dbname}, user={self.user}...')
        io_loop = tornado.ioloop.IOLoop.current()
        self.pool = io_loop.run_sync(partial(
            asyncpg.create_pool,
            dsn=f"postgresql://{self.user}:{self.password}@" \
                f"{self.pghost}:{self.pgport}/{self.dbname}"))
        io_loop.run_sync(partial(self.init_connection))

        if self.sql_file:
            with open(self.sql_file) as stream:
                query = stream.read()
            print(f'Loaded {self.sql_file}')
        else:
            query = self.mvt.generate_sqltomvt_query()

        if self.verbose:
            print(f'Using SQL query:\n\n-------\n\n{query}\n\n-------\n\n')

        application = tornado.web.Application([
            (
                r"/",
                GetMetadata,
                dict(metadata=self.metadata)
            ),
            (
                r"/tiles/([0-9]+)/([0-9]+)/([0-9]+).pbf",
                GetTile,
                dict(pool=self.pool, query=query, key_column=self.key_column,
                     verbose=self.verbose)
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
