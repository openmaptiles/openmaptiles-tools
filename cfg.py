POSTGRES_DB='openmaptiles'
POSTGRES_USER='openmaptiles'
POSTGRES_PASSWORD='openmaptiles'
# POSTGRES_HOST=postgres
POSTGRES_HOST='localhost'
POSTGRES_PORT=5432

'''Path to Wikidata dump'''
DUMP = 'data/latest-all.json.gz'

'''Max number of lines to read from dump'''
LIMIT = 100000000
# LIMIT = 100000

'''OSM tables to fetch Wikidata for'''
OSM_TABLES = ['osm_city_point', 'osm_waterway_linestring']

'''Table with imported wikidata'''
TABLE_NAME = 'wd_names'

