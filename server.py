import tornado.ioloop
import tornado.web
import io
import os

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy import inspect
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

import mercantile
import pyproj
import yaml
import sys
import itertools

def GetTM2Source(file):
    with open(file,'r') as stream:
        tm2source = yaml.load(stream)
    return tm2source

def GeneratePrepared(layers):
    queries = []
    prepared = "PREPARE gettile(geometry, numeric, numeric, numeric) AS "
    for layer in layers['Layer']:
        layer_query = layer['Datasource']['table'].lstrip().rstrip()	# Remove lead and trailing whitespace
        layer_query = layer_query[1:len(layer_query)-6]			# Remove enough characters to remove first and last () and "AS t"
        layer_query = layer_query.replace("geometry", "ST_AsMVTGeom(geometry,!bbox!,4096,0,true) AS mvtgeometry")
        base_query = "SELECT ST_ASMVT('"+layer['id']+"', 4096, 'mvtgeometry', tile) FROM ("+layer_query+" WHERE ST_AsMVTGeom(geometry, !bbox!,4096,0,true) IS NOT NULL) AS tile"
        queries.append(base_query.replace("!bbox!","$1").replace("!scale_denominator!","$2").replace("!pixel_width!","$3").replace("!pixel_height!","$4"))
    prepared = prepared + " UNION ALL ".join(queries) + ";"
    print(prepared)
    return(prepared)

layers = GetTM2Source("/mapping/data.yml")
prepared = GeneratePrepared(layers)
engine = create_engine('postgresql://'+os.getenv('POSTGRES_USER','openmaptiles')+':'+os.getenv('POSTGRES_PASSWORD','openmaptiles')+'@'+os.getenv('POSTGRES_HOST','postgres')+':'+os.getenv('POSTGRES_PORT','5432')+'/'+os.getenv('POSTGRES_DB','openmaptiles'))
inspector = inspect(engine)
DBSession = sessionmaker(bind=engine)
session = DBSession()
session.execute(prepared)

def bounds(zoom,x,y):
    inProj = pyproj.Proj(init='epsg:4326')
    outProj = pyproj.Proj(init='epsg:3857')
    lnglatbbox = mercantile.bounds(x,y,zoom)
    ws = (pyproj.transform(inProj,outProj,lnglatbbox[0],lnglatbbox[1]))
    en = (pyproj.transform(inProj,outProj,lnglatbbox[2],lnglatbbox[3]))
    return {'w':ws[0],'s':ws[1],'e':en[0],'n':en[1]}

def zoom_to_scale_denom(zoom):						# For !scale_denominator!
    # From https://github.com/openstreetmap/mapnik-stylesheets/blob/master/zoom-to-scale.txt
    map_width_in_metres = 40075016.68557849
    tile_width_in_pixels = 256.0
    standardized_pixel_size = 0.00028
    map_width_in_pixels = tile_width_in_pixels*(2.0**zoom)
    return str(map_width_in_metres/(map_width_in_pixels * standardized_pixel_size))

def replace_tokens(query,s,w,n,e,scale_denom):
    return query.replace("!bbox!","ST_MakeBox2D(ST_Point("+w+", "+s+"), ST_Point("+e+", "+n+"))").replace("!scale_denominator!",scale_denom).replace("!pixel_width!","256").replace("!pixel_height!","256")

def get_mvt(zoom,x,y):
    try:								# Sanitize the inputs
        sani_zoom,sani_x,sani_y = float(zoom),float(x),float(y)
        del zoom,x,y
    except:
        print('suspicious')
        return 1

    scale_denom = zoom_to_scale_denom(sani_zoom)
    tilebounds = bounds(sani_zoom,sani_x,sani_y)
    s,w,n,e = str(tilebounds['s']),str(tilebounds['w']),str(tilebounds['n']),str(tilebounds['e'])
    final_query = "EXECUTE gettile(!bbox!, !scale_denominator!, !pixel_width!, !pixel_height!);"
    sent_query = replace_tokens(final_query,s,w,n,e,scale_denom)
    response = list(session.execute(sent_query))
    print(sent_query)
    layers = filter(None,list(itertools.chain.from_iterable(response)))
    final_tile = b''
    for layer in layers:
        final_tile = final_tile + io.BytesIO(layer).getvalue() 
    return final_tile

class GetTile(tornado.web.RequestHandler):
    def get(self, zoom,x,y):
        self.set_header("Content-Type", "application/x-protobuf")
        self.set_header("Content-Disposition", "attachment")
        self.set_header("Access-Control-Allow-Origin", "*")
        response = get_mvt(zoom,x,y)
        self.write(response)

def m():
    if __name__ == "__main__":
        # Make this prepared statement from the tm2source
        application = tornado.web.Application([(r"/tiles/([0-9]+)/([0-9]+)/([0-9]+).pbf", GetTile)])
        print("Postserve started..")
        application.listen(8080)
        tornado.ioloop.IOLoop.instance().start()

m()
