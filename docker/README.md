## Docker Images

##### import-data [![](https://img.shields.io/microbadger/layers/openmaptiles/import-data)](https://hub.docker.com/r/openmaptiles/import-data) [![](https://img.shields.io/microbadger/image-size/openmaptiles/import-data?label=size)](https://hub.docker.com/r/openmaptiles/import-data) [![](https://img.shields.io/docker/pulls/openmaptiles/import-data?label=downloads)](https://hub.docker.com/r/openmaptiles/import-data) [![](https://img.shields.io/docker/stars/openmaptiles/import-data?label=stars)](https://hub.docker.com/r/openmaptiles/import-data)
Multiple data sources packaged for import into PostgreSQL DB, includes data from [Natural Earth](http://www.naturalearthdata.com/), [water polygons](http://osmdata.openstreetmap.de), and [lake centerlines](https://github.com/lukasmartinelli/osm-lakelines).

##### postgis [![](https://img.shields.io/microbadger/layers/openmaptiles/postgis)](https://hub.docker.com/r/openmaptiles/postgis) [![](https://img.shields.io/microbadger/image-size/openmaptiles/postgis?label=size)](https://hub.docker.com/r/openmaptiles/postgis) [![](https://img.shields.io/docker/pulls/openmaptiles/postgis?label=downloads)](https://hub.docker.com/r/openmaptiles/postgis) [![](https://img.shields.io/docker/stars/openmaptiles/postgis?label=stars)](https://hub.docker.com/r/openmaptiles/postgis)
An image with PostgreSQL database, Postgis, and several other extensions, custom built for OpenMapTiles project.
<br><small>Migrated from [postgis](https://github.com/openmaptiles/postgis) repo (archived)</small>

##### postgis-preloaded [![](https://img.shields.io/microbadger/layers/openmaptiles/postgis-preloaded)](https://hub.docker.com/r/openmaptiles/postgis-preloaded) [![](https://img.shields.io/microbadger/image-size/openmaptiles/postgis-preloaded?label=size)](https://hub.docker.com/r/openmaptiles/postgis-preloaded) [![](https://img.shields.io/docker/pulls/openmaptiles/postgis-preloaded?label=downloads)](https://hub.docker.com/r/openmaptiles/postgis-preloaded) [![](https://img.shields.io/docker/stars/openmaptiles/postgis-preloaded?label=stars)](https://hub.docker.com/r/openmaptiles/postgis-preloaded)
The above `postgis` image pre-loaded with the `import-data`. This image is mostly used for testing, and may not be appropriate for production. The image has hardcoded user `openmaptiles` and password `openmaptiles`.

##### generate-vectortiles [![](https://img.shields.io/microbadger/layers/openmaptiles/generate-vectortiles)](https://hub.docker.com/r/openmaptiles/generate-vectortiles) [![](https://img.shields.io/microbadger/image-size/openmaptiles/generate-vectortiles?label=size)](https://hub.docker.com/r/openmaptiles/generate-vectortiles) [![](https://img.shields.io/docker/pulls/openmaptiles/generate-vectortiles?label=downloads)](https://hub.docker.com/r/openmaptiles/generate-vectortiles) [![](https://img.shields.io/docker/stars/openmaptiles/generate-vectortiles?label=stars)](https://hub.docker.com/r/openmaptiles/generate-vectortiles)
Legacy Mapnik-based image that simplifies `tilelive-copy` tile generation.  Eventually will be replaced with PostgreSQL-based [ST_AsMVT](https://postgis.net/docs/ST_AsMVT.html) approach. 
<br><small>Migrated from [generate-vectortiles](https://github.com/openmaptiles/generate-vectortiles) repo (archived)</small>


# Deprecated Legacy Tools
These Docker images are no longer maintained or published, and should not be used.

## [import-sql](https://hub.docker.com/r/openmaptiles/import-sql)
Use [import-sql](../README.md#importing-into-postgres) in the `openmaptiles-tools` image instead of `import_sql.sh`.  Originally migrated from [import-sql](https://github.com/openmaptiles/import-sql) repo.

## [import-wikidata](https://hub.docker.com/r/openmaptiles/import-wikidata)
Use [import-wikidata](../README.md#import-wikidata-localized-names) in the `openmaptiles-tools` image instead.  Originally migrated from [import-wikidata](https://github.com/openmaptiles/import-wikidata) repo.

## [import-lakelines](https://hub.docker.com/r/openmaptiles/import-lakelines)
Use `openmaptiles-data` image instead.  Originally migrated from  [import-lakelines](https://github.com/openmaptiles/import-lakelines) repo.

## [import-natural-earth](https://hub.docker.com/r/openmaptiles/import-natural-earth)
Use `openmaptiles-data` image instead.  Originally migrated from [import-natural-earth](https://github.com/openmaptiles/import-natural-earth) repo.

## [import-water](https://hub.docker.com/r/openmaptiles/import-water)
Use `openmaptiles-data` image instead.  Originally migrated from [import-water](https://github.com/openmaptiles/import-water) repo.

## [generate-osmborder](https://hub.docker.com/r/openmaptiles/generate-osmborder) and [import-osmborder](https://hub.docker.com/r/openmaptiles/import-osmborder)
Use [import-borders](../README.md#import-osm-borders) in the `openmaptiles-tools` image instead.  Originally migrated from [import-osmborder](https://github.com/openmaptiles/import-osmborder) repo.

## [import-osm](https://hub.docker.com/r/openmaptiles/import-osm)
Use [import-osm](../README.md#import-and-update-osm-data) in the `openmaptiles-tools` image instead.  Originally migrated from [import-osm](https://github.com/openmaptiles/import-osm).
