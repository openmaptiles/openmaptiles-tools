import logging
from functools import partial
from typing import Union, List, Any, Dict

from asyncpg import Connection, ConnectionDoesNotExistError, PostgresLogMessage, \
    create_pool
from asyncpg.pool import Pool
# noinspection PyUnresolvedReferences
from tornado.ioloop import IOLoop
# noinspection PyUnresolvedReferences
from tornado.log import access_log
# noinspection PyUnresolvedReferences
from tornado.web import Application, RequestHandler

from openmaptiles.pgutils import show_settings, get_postgis_version, PgWarnings, \
    get_vector_layers
from openmaptiles.sqltomvt import MvtGenerator
from openmaptiles.tileset import Tileset


class RequestHandledWithCors(RequestHandler):
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'GET, OPTIONS')

    def options(self):
        self.set_status(204)
        self.finish()

    def head(self):
        # TODO: Technically here we should do a full tile/metadata retrieval,
        # but without sending the actual content back.
        # We must implement it to support QGIS
        self.finish()


class GetTile(RequestHandledWithCors):
    pool: Pool
    query: str
    key_column: str
    test_geometry: bool
    gzip: bool
    verbose: bool
    connection: Union[Connection, None]
    cancelled: bool

    def initialize(self, pool, query, key_column, gzip, verbose, test_geometry):
        self.pool = pool
        self.query = query
        self.key_column = key_column
        self.gzip = gzip
        self.test_geometry = test_geometry
        self.verbose = verbose
        self.connection = None
        self.cancelled = False

    async def get(self, zoom, x, y):
        messages: List[PostgresLogMessage] = []

        def logger(_, log_msg: PostgresLogMessage):
            messages.append(log_msg)

        self.set_header("Content-Type", "application/x-protobuf")
        self.set_header("Content-Disposition", "attachment")
        self.set_header("Access-Control-Allow-Origin", "*")
        try:
            async with self.pool.acquire() as connection:
                connection.add_log_listener(logger)
                self.connection = connection
                query = self.query
                zoom, x, y = int(zoom), int(x), int(y)
                if self.verbose:
                    # Make it easier to track queries in pg_stat_activity table
                    query = f"/* {zoom}/{x}/{y} */ " + query
                if self.key_column or self.test_geometry:
                    row = await connection.fetchrow(query, zoom, x, y)
                    tile = row['mvt']
                    key = row['key'] if self.key_column else None
                    bad_geos = row['bad_geos'] if self.test_geometry else 0
                else:
                    tile = await connection.fetchval(query, zoom, x, y)
                    key = None
                    bad_geos = 0
                if tile:
                    if self.gzip:
                        self.set_header("content-encoding", "gzip")
                    if key:
                        # Report strong validation, see
                        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/ETag
                        self.set_header("ETag", f'"{key}"')
                    self.write(tile)

                    if self.verbose or bad_geos > 0 or messages:
                        print(f"Tile {zoom}/{x}/{y}"
                              f"{f' key={key}' if self.key_column else ''} "
                              f"is {len(tile):,} bytes"
                              f"{bad_geos and f' has {bad_geos} bad geometries' or ''}"
                              )
                else:
                    self.set_status(204)
                    if self.verbose or messages:
                        print(f"Tile {zoom}/{x}/{y} is empty.")
                for msg in messages:
                    PgWarnings.print_message(msg)
                connection.remove_log_listener(logger)

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
    metadata: Dict[str, Any]
    generated_query: str

    def __init__(self, url, port, pghost, pgport, dbname, user, password,
                 layers, tileset_path, sql_file, key_column, disable_feature_ids,
                 gzip, verbose, exclude_layers, test_geometry):
        self.url = url
        self.port = port
        self.pghost = pghost
        self.pgport = pgport
        self.dbname = dbname
        self.user = user
        self.password = password
        self.tileset_path = tileset_path
        self.sql_file = sql_file
        self.layer_ids = layers
        self.exclude_layers = exclude_layers
        self.key_column = key_column
        self.gzip = gzip
        self.disable_feature_ids = disable_feature_ids
        self.test_geometry = test_geometry
        self.verbose = verbose

        self.tileset = Tileset.parse(self.tileset_path)

    def create_metadata(self,
                        urls: List[str],
                        vector_layers: List[dict],
                        ) -> Dict[str, Any]:
        """Convert tileset to the tilejson spec
           https://github.com/mapbox/tilejson-spec/tree/master/2.2.0#2-file-format
           A few optional parameters were removed as irrelevant
        """
        return {
            # REQUIRED. A semver.org style version number. Describes the version of
            # the TileJSON spec that is implemented by this JSON object.
            "tilejson": "2.2.0",

            # OPTIONAL. Default: null. A name describing the tileset. The name can
            # contain any legal character. Implementations SHOULD NOT interpret the
            # name as HTML.
            "name": self.tileset.name,

            # OPTIONAL. Default: null. A text description of the tileset. The
            # description can contain any legal character. Implementations SHOULD NOT
            # interpret the description as HTML.
            "description": self.tileset.description,

            # OPTIONAL. Default: "1.0.0". A semver.org style version number. When
            # changes across tiles are introduced, the minor version MUST change.
            # This may lead to cut off labels. Therefore, implementors can decide to
            # clean their cache when the minor version changes. Changes to the patch
            # level MUST only have changes to tiles that are contained within one tile.
            # When tiles change significantly, the major version MUST be increased.
            # Implementations MUST NOT use tiles with different major versions.
            "version": self.tileset.version,

            # OPTIONAL. Default: null. Contains an attribution to be displayed
            # when the map is shown to a user. Implementations MAY decide to treat this
            # as HTML or literal text. For security reasons, make absolutely sure that
            # this field can't be abused as a vector for XSS or beacon tracking.
            "attribution": self.tileset.attribution,

            # REQUIRED. An array of tile endpoints. {z}, {x} and {y}, if present,
            # are replaced with the corresponding integers. If multiple endpoints are specified, clients
            # may use any combination of endpoints. All endpoints MUST return the same
            # content for the same URL. The array MUST contain at least one endpoint.
            "tiles": urls,

            # OPTIONAL. Default: 0. >= 0, <= 30.
            # An integer specifying the minimum zoom level.
            "minzoom": self.tileset.minzoom,

            # OPTIONAL. Default: 30. >= 0, <= 30.
            # An integer specifying the maximum zoom level. MUST be >= minzoom.
            "maxzoom": self.tileset.maxzoom,

            # OPTIONAL. Default: [-180, -90, 180, 90].
            # The maximum extent of available map tiles. Bounds MUST define an area
            # covered by all zoom levels. The bounds are represented in WGS:84
            # latitude and longitude values, in the order left, bottom, right, top.
            # Values may be integers or floating point numbers.
            "bounds": self.tileset.bounds,

            # OPTIONAL. Default: null.
            # The first value is the longitude, the second is latitude (both in
            # WGS:84 values), the third value is the zoom level as an integer.
            # Longitude and latitude MUST be within the specified bounds.
            # The zoom level MUST be between minzoom and maxzoom.
            # Implementations can use this value to set the default location. If the
            # value is null, implementations may use their own algorithm for
            # determining a default location.
            "center": self.tileset.center,

            # This is an undocumented extension to the 2.2 spec that is often used:
            # https://github.com/mapbox/tilejson-spec/issues/14
            "vector_layers": vector_layers,
        }

    async def init_connection(self):
        async with self.pool.acquire() as conn:
            await show_settings(conn)
            mvt = MvtGenerator(
                self.tileset,
                postgis_ver=await get_postgis_version(conn),
                zoom='$1', x='$2', y='$3',
                layer_ids=self.layer_ids,
                key_column=self.key_column,
                gzip=self.gzip,
                use_feature_id=False if self.disable_feature_ids else None,
                test_geometry=self.test_geometry,
                exclude_layers=self.exclude_layers,
            )
            self.generated_query = mvt.generate_sql()
            self.metadata = self.create_metadata(
                [self.url + "/tiles/{z}/{x}/{y}.pbf"],
                await get_vector_layers(conn, mvt))

    def serve(self):
        access_log.setLevel(logging.INFO if self.verbose else logging.ERROR)

        print(f'Connecting to PostgreSQL at {self.pghost}:{self.pgport}, '
              f'db={self.dbname}, user={self.user}...')
        io_loop = IOLoop.current()
        self.pool = io_loop.run_sync(partial(
            create_pool,
            dsn=f"postgresql://{self.user}:{self.password}@"
                f"{self.pghost}:{self.pgport}/{self.dbname}"))
        io_loop.run_sync(partial(self.init_connection))

        if self.sql_file:
            with open(self.sql_file) as stream:
                query = stream.read()
            print(f'Loaded {self.sql_file}')
        else:
            query = self.generated_query

        if self.verbose:
            print(f'Using SQL query:\n\n-------\n\n{query}\n\n-------\n\n')

        application = Application([
            (
                r"/",
                GetMetadata,
                dict(metadata=self.metadata)
            ),
            (
                r"/tiles/([0-9]+)/([0-9]+)/([0-9]+).pbf",
                GetTile,
                dict(pool=self.pool, query=query, key_column=self.key_column,
                     gzip=self.gzip, test_geometry=self.test_geometry,
                     verbose=self.verbose)
            ),
        ])

        application.listen(self.port)
        print(f"Postserve started, listening on 0.0.0.0:{self.port}")
        print(f"Use {self.url} as the data source")
        IOLoop.instance().start()
