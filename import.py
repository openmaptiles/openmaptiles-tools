#!/usr/bin/env python
import psycopg2.extras
from wikidata import etl, osm
from cfg import *

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
