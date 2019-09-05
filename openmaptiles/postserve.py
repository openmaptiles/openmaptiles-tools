import logging
import io
import psycopg2
import tornado.ioloop
import tornado.web
from datetime import datetime

from openmaptiles.consts import PIXEL_SCALE
from openmaptiles.language import languages_to_sql
from openmaptiles.sqltomvt import generate_sqltomvt_preparer
from openmaptiles.tileset import Tileset


# noinspection PyAbstractClass
class RequestHandledWithCors(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'GET, OPTIONS')

    def options(self):
        self.set_status(204)
        self.finish()


# noinspection PyAbstractClass
class GetTile(RequestHandledWithCors):

    # noinspection PyAttributeOutsideInit
    def initialize(self, fname, connection, query):
        self.fname = fname
        self.db_connection = connection
        self.db_query = query

    def get(self, z, x, y):
        start = datetime.utcnow()
        elapsed = lambda: str(datetime.utcnow() - start)
        z, x, y = int(z), int(x), int(y)
        cursor = self.db_connection.cursor()
        try:
            cursor.execute(self.db_query, (z, x, y))
            result = cursor.fetchall()
            if result:
                self.set_header("Content-Type", "application/x-protobuf")
                self.set_header("Content-Disposition", "attachment")
                value = io.BytesIO(result[0][0]).getvalue()
                self.write(value)
                print(f'{len(value): >8,} bytes, {elapsed(): >16},  {f"{self.fname}({z},{x},{y})"}')
            else:
                self.clear()
                self.set_status(404)
                print(f'{self.fname}({z},{x},{y}) is EMPTY, time={elapsed()}')
        except Exception as err:
            print(f'{self.fname}({z},{x},{y}) threw an exception, time={elapsed()}')
            raise
        finally:
            cursor.close()


# noinspection PyAbstractClass
class GetMetadata(RequestHandledWithCors):

    # noinspection PyAttributeOutsideInit
    def initialize(self, metadata):
        self.metadata = metadata

    def get(self):
        self.write(self.metadata)
        print('Returning metadata')


def serve(port, pghost, pgport, dbname, user, password, metadata, tileset_path, sql_file, mask_layer, mask_zoom,
          verbose):
    fname = 'getTile'
    tileset = Tileset.parse(tileset_path)

    if sql_file:
        with open(sql_file) as stream:
            prepared_sql = stream.read()
        print(f'Loaded {sql_file}')
    else:
        prepared_sql = generate_sqltomvt_preparer({
            'tileset': tileset,
            'fname': fname,
            'mask-layer': mask_layer,
            'mask-zoom': mask_zoom,
        })

    print(f'Connecting to PostgreSQL at {pghost}:{pgport}, db={dbname}, user={user}...')
    connection = psycopg2.connect(
        dbname=dbname,
        host=pghost,
        port=pgport,
        user=user,
        password=password,
    )
    cursor = connection.cursor()

    # Get all Postgres types and keep those we know about (could be optimized further)
    known_types = dict(bool="Boolean", text="String", int4="Number", int8="Number")
    cursor.execute("select oid, typname from pg_type")
    pg_types = {row[0]: known_types[row[1]] for row in cursor.fetchall() if row[1] in known_types}

    vector_layers = []
    for layer_def in tileset.layers:
        layer = layer_def["layer"]

        # Get field names and types by executing a dummy query
        query = (layer['datasource']['query']
                 .format(name_languages=languages_to_sql(tileset.definition.get('languages', [])))
                 .replace("!bbox!", "TileBBox(0, 0, 0)")
                 .replace("z(!scale_denominator!)", "0")
                 .replace("!pixel_width!", str(PIXEL_SCALE))
                 .replace("!pixel_height!", str(PIXEL_SCALE)))
        cursor.execute(f"SELECT * FROM {query} WHERE false LIMIT 0")
        fields = {fld.name: pg_types[fld.type_code] for fld in cursor.description if fld.type_code in pg_types}

        vector_layers.append(dict(
            id=layer["id"],
            fields=fields,
            maxzoom=metadata["maxzoom"],
            minzoom=metadata["minzoom"],
            description=layer["description"],
        ))

    metadata["vector_layers"] = vector_layers
    metadata["tiles"] = [f"http://localhost:{port}" + "/tiles/{z}/{x}/{y}.pbf"]

    if verbose:
        print(f'Using prepared SQL:\n\n-------\n\n{prepared_sql}\n\n-------\n\n')

    try:
        cursor.execute(prepared_sql)
    finally:
        cursor.close()

    query = f"EXECUTE {fname}(%s, %s, %s)"
    print(f'Will use "{query}" to get vector tiles.')

    tornado.log.access_log.setLevel(logging.INFO if verbose else logging.ERROR)

    application = tornado.web.Application([
        (
            r"/",
            GetMetadata,
            dict(metadata=metadata)
        ),
        (
            r"/tiles/([0-9]+)/([0-9]+)/([0-9]+).pbf",
            GetTile,
            dict(fname=fname, connection=connection, query=query)
        ),
    ])

    application.listen(port)
    print(f"Postserve started, listening on 0.0.0.0:{port}")
    print(f"Use http://localhost:{port} as the data source")

    tornado.ioloop.IOLoop.instance().start()
