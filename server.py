import tornado.ioloop
import tornado.web
import io
import os

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

import mercantile
import pyproj
import sys
import itertools


def getPreparedSql(file):
    with open(file, 'r') as stream:
        return stream.read()


prepared = getPreparedSql("/mapping/mvt/maketile_prep.sql")
engine = create_engine(
    'postgresql://' + os.getenv('POSTGRES_USER', 'openmaptiles') +
    ':' + os.getenv('POSTGRES_PASSWORD', 'openmaptiles') +
    '@' + os.getenv('POSTGRES_HOST', 'postgres') +
    ':' + os.getenv('POSTGRES_PORT', '5432') +
    '/' + os.getenv('POSTGRES_DB', 'openmaptiles'))
inspector = inspect(engine)
DBSession = sessionmaker(bind=engine)
session = DBSession()
session.execute(prepared)


def bounds(zoom, x, y):
    inProj = pyproj.Proj(init='epsg:4326')
    outProj = pyproj.Proj(init='epsg:3857')
    lnglatbbox = mercantile.bounds(x, y, zoom)
    ws = (pyproj.transform(inProj, outProj, lnglatbbox[0], lnglatbbox[1]))
    en = (pyproj.transform(inProj, outProj, lnglatbbox[2], lnglatbbox[3]))
    return {'w': ws[0], 's': ws[1], 'e': en[0], 'n': en[1]}


def replace_tokens(query, s, w, n, e, zoom):
    return (query
            .replace("!bbox!", "ST_MakeBox2D(ST_Point(" + w + ", " + s + "), ST_Point(" + e + ", " + n + "))")
            .replace("!zoom!", zoom)
            .replace("!pixel_width!", "256"))


def get_mvt(zoom, x, y):
    try:
        # Sanitize the inputs
        sani_zoom, sani_x, sani_y = float(zoom), float(x), float(y)
        del zoom, x, y
    except:
        print('suspicious')
        return 1

    tilebounds = bounds(sani_zoom, sani_x, sani_y)
    s, w, n, e = str(tilebounds['s']), str(tilebounds['w']), str(tilebounds['n']), str(tilebounds['e'])
    final_query = "EXECUTE gettile(!bbox!, !zoom!, !pixel_width!);"
    sent_query = replace_tokens(final_query, s, w, n, e, sani_zoom)
    response = list(session.execute(sent_query))
    print(sent_query)
    layers = filter(None, list(itertools.chain.from_iterable(response)))
    final_tile = b''
    for layer in layers:
        final_tile = final_tile + io.BytesIO(layer).getvalue()
    return final_tile


class GetTile(tornado.web.RequestHandler):
    def get(self, zoom, x, y):
        self.set_header("Content-Type", "application/x-protobuf")
        self.set_header("Content-Disposition", "attachment")
        self.set_header("Access-Control-Allow-Origin", "*")
        response = get_mvt(zoom, x, y)
        self.write(response)


def m():
    if __name__ == "__main__":
        application = tornado.web.Application([(r"/tiles/([0-9]+)/([0-9]+)/([0-9]+).pbf", GetTile)])
        print("Postserve started..")
        application.listen(8080)
        tornado.ioloop.IOLoop.instance().start()


m()
