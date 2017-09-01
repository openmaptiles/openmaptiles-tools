#!/usr/bin/env python
import psycopg2.extras
from wikidata import etl, osm

POSTGRES_DB='openmaptiles'
POSTGRES_USER='openmaptiles'
POSTGRES_PASSWORD='openmaptiles'
# POSTGRES_HOST=postgres
POSTGRES_HOST='localhost'
POSTGRES_PORT=5432

'''Max number of rows to read from dump'''
LIMIT = 100000000
# LIMIT = 100000

'''OSM tables to fetch Wikidata for'''
OSM_TABLES = ['osm_city_point', 'osm_waterway_linestring']

'''Table with imported wikidata'''
TABLE_NAME = 'wd_names'

DUMP = 'data/latest-all.json.gz'

conn = psycopg2.connect(dbname=POSTGRES_DB, user=POSTGRES_USER,
                        password=POSTGRES_PASSWORD, host=POSTGRES_HOST,
                        port=POSTGRES_PORT)

psycopg2.extras.register_hstore(conn)
cur = conn.cursor()

ids = osm.get_ids(OSM_TABLES, cur)
pages = osm.get_pages(OSM_TABLES, cur)

etl.recreate_table(TABLE_NAME, cur)
conn.commit()
etl.simple_parse(DUMP, ids, pages, cur, conn, TABLE_NAME, LIMIT)

cur.close()
conn.close()
