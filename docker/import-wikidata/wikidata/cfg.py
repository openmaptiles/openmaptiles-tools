import os

# Backward compatibility - for now, allow POSTGRES_* env if set, or use standard PG*
POSTGRES_DB = os.getenv('POSTGRES_DB') or os.environ['PGDATABASE']
POSTGRES_USER = os.getenv('POSTGRES_USER') or os.environ['PGUSER']
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD') or os.environ['PGPASSWORD']
POSTGRES_HOST = os.getenv('POSTGRES_HOST') or os.environ['PGHOST']
POSTGRES_PORT = os.getenv('POSTGRES_PORT') or os.getenv('PGPORT') or '5432'

'''Path to Wikidata dump from /import folder'''
DUMP = 'latest-all.json.gz'

'''Max number of lines to read from dump'''
LIMIT = 100000000
# LIMIT = 1000000

'''OSM tables to fetch Wikidata for'''
OSM_TABLES = [
    'osm_aerodrome_label_point',
    'osm_peak_point',
    'osm_city_point',
    'osm_continent_point',
    'osm_country_point',
    'osm_island_point',
    'osm_island_polygon',
    'osm_state_point',
    'osm_poi_point',
    'osm_poi_polygon',
    'osm_marine_point',
    'osm_water_polygon',
    'osm_waterway_linestring'
]

'''Table with imported wikidata'''
TABLE_NAME = 'wd_names'
