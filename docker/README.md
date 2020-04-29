# Docker Images / Importers

Each subdir here creates a docker image that either generates some data, or is built with some pre-computed dataset. For example, the `import-natural-earth` image downloads and cleans up data from the [Natural Earth project](https://www.naturalearthdata.com/). When ran, the image injects the packaged data into PostgreSQL database, without additional downloading and preprocessing.

## [import-data](import-data)
[![](https://img.shields.io/docker/cloud/build/openmaptiles/import-data?&logo=OpenStreetMap&label=build)](https://hub.docker.com/r/openmaptiles/import-data)
[![](https://img.shields.io/docker/automated/openmaptiles/import-data?label=build)](https://hub.docker.com/r/openmaptiles/import-data/builds)
[![](https://img.shields.io/microbadger/layers/openmaptiles/import-data)](https://hub.docker.com/r/openmaptiles/import-data)
[![](https://img.shields.io/microbadger/image-size/openmaptiles/import-data?label=size)](https://hub.docker.com/r/openmaptiles/import-data)
[![](https://img.shields.io/docker/pulls/openmaptiles/import-data?label=downloads)](https://hub.docker.com/r/openmaptiles/import-data)
[![](https://img.shields.io/docker/stars/openmaptiles/import-data?label=stars)](https://hub.docker.com/r/openmaptiles/import-data)

# Tools

## [generate-vectortiles](generate-vectortiles)
[![](https://img.shields.io/docker/cloud/build/openmaptiles/generate-vectortiles?&logo=OpenStreetMap&label=build)](https://hub.docker.com/r/openmaptiles/generate-vectortiles)
[![](https://img.shields.io/docker/automated/openmaptiles/generate-vectortiles?label=build)](https://hub.docker.com/r/openmaptiles/generate-vectortiles/builds)
[![](https://img.shields.io/microbadger/layers/openmaptiles/generate-vectortiles)](https://hub.docker.com/r/openmaptiles/generate-vectortiles)
[![](https://img.shields.io/microbadger/image-size/openmaptiles/generate-vectortiles?label=size)](https://hub.docker.com/r/openmaptiles/generate-vectortiles)
[![](https://img.shields.io/docker/pulls/openmaptiles/generate-vectortiles?label=downloads)](https://hub.docker.com/r/openmaptiles/generate-vectortiles)
[![](https://img.shields.io/docker/stars/openmaptiles/generate-vectortiles?label=stars)](https://hub.docker.com/r/openmaptiles/generate-vectortiles)
<br><small>Migrated from [generate-vectortiles](https://github.com/openmaptiles/generate-vectortiles) repo (archived)</small>

## [postgis](postgis)
[![](https://img.shields.io/docker/cloud/build/openmaptiles/postgis?&logo=OpenStreetMap&label=build)](https://hub.docker.com/r/openmaptiles/postgis)
[![](https://img.shields.io/docker/automated/openmaptiles/postgis?label=build)](https://hub.docker.com/r/openmaptiles/postgis/builds)
[![](https://img.shields.io/microbadger/layers/openmaptiles/postgis)](https://hub.docker.com/r/openmaptiles/postgis)
[![](https://img.shields.io/microbadger/image-size/openmaptiles/postgis?label=size)](https://hub.docker.com/r/openmaptiles/postgis)
[![](https://img.shields.io/docker/pulls/openmaptiles/postgis?label=downloads)](https://hub.docker.com/r/openmaptiles/postgis)
[![](https://img.shields.io/docker/stars/openmaptiles/postgis?label=stars)](https://hub.docker.com/r/openmaptiles/postgis)
<br><small>Migrated from [postgis](https://github.com/openmaptiles/postgis) repo (archived)</small>

## [postgis-preloaded](postgis-preloaded)
[![](https://img.shields.io/docker/cloud/build/openmaptiles/postgis-preloaded?&logo=OpenStreetMap&label=build)](https://hub.docker.com/r/openmaptiles/postgis-preloaded)
[![](https://img.shields.io/docker/automated/openmaptiles/postgis-preloaded?label=build)](https://hub.docker.com/r/openmaptiles/postgis-preloaded/builds)
[![](https://img.shields.io/microbadger/layers/openmaptiles/postgis-preloaded)](https://hub.docker.com/r/openmaptiles/postgis-preloaded)
[![](https://img.shields.io/microbadger/image-size/openmaptiles/postgis-preloaded?label=size)](https://hub.docker.com/r/openmaptiles/postgis-preloaded)
[![](https://img.shields.io/docker/pulls/openmaptiles/postgis-preloaded?label=downloads)](https://hub.docker.com/r/openmaptiles/postgis-preloaded)
[![](https://img.shields.io/docker/stars/openmaptiles/postgis-preloaded?label=stars)](https://hub.docker.com/r/openmaptiles/postgis-preloaded)

A data-preloaded database image used mostly for testing. The image is based on the `postgis` image above, initialized with the `openmaptiles` database (user=openmaptiles, password=openmaptiles), preloaded with water, lakelines, and natural-earth data.

# Deprecated Legacy Tools
These Docker images are no longer maintained or published, and should not be used.

## [import-sql](https://hub.docker.com/r/openmaptiles/import-sql)
Use [import-sql](../README.md#importing-into-postgres) in the `openmaptiles-tools` image instead of `import_sql.sh`.  Originally migrated from [import-sql](https://github.com/openmaptiles/import-sql) repo.

## [import-wikidata](https://hub.docker.com/r/openmaptiles/import-wikidata)
Use [import-wikidata](../README.md#import-wikidata-localized-names) in the `openmaptiles-tools` image instead.  Originally migrated from [import-wikidata](https://github.com/openmaptiles/import-wikidata) repo.

## [import-lakelines](https://hub.docker.com/r/openmaptiles/import-lakelines)
Use `openmaptiles-data` image instead.  Originally migrated from  [import-lakelines](https://github.com/openmaptiles/import-lakelines) repo.

## [import-natural-earth](import-natural-earth)
Use `openmaptiles-data` image instead.  Originally migrated from [import-natural-earth](https://github.com/openmaptiles/import-natural-earth) repo.

## [import-water](import-water)
Use `openmaptiles-data` image instead.  Originally migrated from [import-water](https://github.com/openmaptiles/import-water) repo.

## [generate-osmborder](https://hub.docker.com/r/openmaptiles/generate-osmborder) and [import-osmborder](https://hub.docker.com/r/openmaptiles/import-osmborder)
Use [import-borders](../README.md#import-osm-borders) in the `openmaptiles-tools` image instead.  Originally migrated from [import-osmborder](https://github.com/openmaptiles/import-osmborder) repo.

## [import-osm](https://hub.docker.com/r/openmaptiles/import-osm)
Use [import-osm](../README.md#import-and-update-osm-data) in the `openmaptiles-tools` image instead.  Originally migrated from [import-osm](https://github.com/openmaptiles/import-osm).
