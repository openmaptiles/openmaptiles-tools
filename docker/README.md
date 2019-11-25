# Docker Images / Importers

Each subdir here creates a docker image that either generates some data, or is built with some pre-computed dataset. For example, the `import-natural-earth` image downloads and cleans up data from the [Natural Earth project](https://www.naturalearthdata.com/). When ran, the image injects the packaged data into PostgreSQL database, without additional downloading and preprocessing.

## [import-lakelines](import-lakelines)
[![](https://img.shields.io/docker/cloud/build/openmaptiles/import-lakelines?&logo=OpenStreetMap&label=build)](https://hub.docker.com/repository/docker/openmaptiles/import-lakelines)
[![](https://img.shields.io/docker/automated/openmaptiles/import-lakelines?label=build)](https://hub.docker.com/repository/docker/openmaptiles/import-lakelines/builds)
[![](https://img.shields.io/microbadger/layers/openmaptiles/import-lakelines)](https://hub.docker.com/repository/docker/openmaptiles/import-lakelines)
[![](https://img.shields.io/microbadger/image-size/openmaptiles/import-lakelines?label=size)](https://hub.docker.com/repository/docker/openmaptiles/import-lakelines)
[![](https://img.shields.io/docker/pulls/openmaptiles/import-lakelines?label=downloads)](https://hub.docker.com/repository/docker/openmaptiles/import-lakelines)
[![](https://img.shields.io/docker/stars/openmaptiles/import-lakelines?label=stars)](https://hub.docker.com/repository/docker/openmaptiles/import-lakelines)
<br><small>Migrated from [import-lakelines](https://github.com/openmaptiles/import-lakelines) repo (archived)</small>

## [import-natural-earth](import-natural-earth)
[![](https://img.shields.io/docker/cloud/build/openmaptiles/import-natural-earth?&logo=OpenStreetMap&label=build)](https://hub.docker.com/repository/docker/openmaptiles/import-natural-earth)
[![](https://img.shields.io/docker/automated/openmaptiles/import-natural-earth?label=build)](https://hub.docker.com/repository/docker/openmaptiles/import-natural-earth/builds)
[![](https://img.shields.io/microbadger/layers/openmaptiles/import-natural-earth)](https://hub.docker.com/repository/docker/openmaptiles/import-natural-earth)
[![](https://img.shields.io/microbadger/image-size/openmaptiles/import-natural-earth?label=size)](https://hub.docker.com/repository/docker/openmaptiles/import-natural-earth)
[![](https://img.shields.io/docker/pulls/openmaptiles/import-natural-earth?label=downloads)](https://hub.docker.com/repository/docker/openmaptiles/import-natural-earth)
[![](https://img.shields.io/docker/stars/openmaptiles/import-natural-earth?label=stars)](https://hub.docker.com/repository/docker/openmaptiles/import-natural-earth)
<br><small>Migrated from [import-natural-earth](https://github.com/openmaptiles/import-natural-earth) repo (archived)</small>

## [import-osm](import-osm)
[![](https://img.shields.io/docker/cloud/build/openmaptiles/import-osm?&logo=OpenStreetMap&label=build)](https://hub.docker.com/repository/docker/openmaptiles/import-osm)
[![](https://img.shields.io/docker/automated/openmaptiles/import-osm?label=build)](https://hub.docker.com/repository/docker/openmaptiles/import-osm/builds)
[![](https://img.shields.io/microbadger/layers/openmaptiles/import-osm)](https://hub.docker.com/repository/docker/openmaptiles/import-osm)
[![](https://img.shields.io/microbadger/image-size/openmaptiles/import-osm?label=size)](https://hub.docker.com/repository/docker/openmaptiles/import-osm)
[![](https://img.shields.io/docker/pulls/openmaptiles/import-osm?label=downloads)](https://hub.docker.com/repository/docker/openmaptiles/import-osm)
[![](https://img.shields.io/docker/stars/openmaptiles/import-osm?label=stars)](https://hub.docker.com/repository/docker/openmaptiles/import-osm)
<br><small>Migrated from [import-osm](https://github.com/openmaptiles/import-osm) repo (archived)</small>

## [import-osmborder](import-osmborder)
[![](https://img.shields.io/docker/cloud/build/openmaptiles/import-osmborder?&logo=OpenStreetMap&label=build)](https://hub.docker.com/repository/docker/openmaptiles/import-osmborder)
[![](https://img.shields.io/docker/automated/openmaptiles/import-osmborder?label=build)](https://hub.docker.com/repository/docker/openmaptiles/import-osmborder/builds)
[![](https://img.shields.io/microbadger/layers/openmaptiles/import-osmborder)](https://hub.docker.com/repository/docker/openmaptiles/import-osmborder)
[![](https://img.shields.io/microbadger/image-size/openmaptiles/import-osmborder?label=size)](https://hub.docker.com/repository/docker/openmaptiles/import-osmborder)
[![](https://img.shields.io/docker/pulls/openmaptiles/import-osmborder?label=downloads)](https://hub.docker.com/repository/docker/openmaptiles/import-osmborder)
[![](https://img.shields.io/docker/stars/openmaptiles/import-osmborder?label=stars)](https://hub.docker.com/repository/docker/openmaptiles/import-osmborder)
<br><small>Migrated from [import-osmborder](https://github.com/openmaptiles/import-osmborder) repo, `/import` dir (archived)</small>

## [import-sql](import-sql)
[![](https://img.shields.io/docker/cloud/build/openmaptiles/import-sql?&logo=OpenStreetMap&label=build)](https://hub.docker.com/repository/docker/openmaptiles/import-sql)
[![](https://img.shields.io/docker/automated/openmaptiles/import-sql?label=build)](https://hub.docker.com/repository/docker/openmaptiles/import-sql/builds)
[![](https://img.shields.io/microbadger/layers/openmaptiles/import-sql)](https://hub.docker.com/repository/docker/openmaptiles/import-sql)
[![](https://img.shields.io/microbadger/image-size/openmaptiles/import-sql?label=size)](https://hub.docker.com/repository/docker/openmaptiles/import-sql)
[![](https://img.shields.io/docker/pulls/openmaptiles/import-sql?label=downloads)](https://hub.docker.com/repository/docker/openmaptiles/import-sql)
[![](https://img.shields.io/docker/stars/openmaptiles/import-sql?label=stars)](https://hub.docker.com/repository/docker/openmaptiles/import-sql)
<br><small>Migrated from [import-sql](https://github.com/openmaptiles/import-sql) repo (archived)</small>

**Note:** This image is obsolete, and should not be used. Use `openmaptiles-tools` image instead. `import_sql.sh` was copied to `/bin` as `import-sql`.

## [import-water](import-water)
[![](https://img.shields.io/docker/cloud/build/openmaptiles/import-water?&logo=OpenStreetMap&label=build)](https://hub.docker.com/repository/docker/openmaptiles/import-water)
[![](https://img.shields.io/docker/automated/openmaptiles/import-water?label=build)](https://hub.docker.com/repository/docker/openmaptiles/import-water/builds)
[![](https://img.shields.io/microbadger/layers/openmaptiles/import-water)](https://hub.docker.com/repository/docker/openmaptiles/import-water)
[![](https://img.shields.io/microbadger/image-size/openmaptiles/import-water?label=size)](https://hub.docker.com/repository/docker/openmaptiles/import-water)
[![](https://img.shields.io/docker/pulls/openmaptiles/import-water?label=downloads)](https://hub.docker.com/repository/docker/openmaptiles/import-water)
[![](https://img.shields.io/docker/stars/openmaptiles/import-water?label=stars)](https://hub.docker.com/repository/docker/openmaptiles/import-water)
<br><small>Migrated from [import-water](https://github.com/openmaptiles/import-water) repo (archived)</small>

## [import-wikidata](import-wikidata)
[![](https://img.shields.io/docker/cloud/build/openmaptiles/import-wikidata?&logo=OpenStreetMap&label=build)](https://hub.docker.com/repository/docker/openmaptiles/import-wikidata)
[![](https://img.shields.io/docker/automated/openmaptiles/import-wikidata?label=build)](https://hub.docker.com/repository/docker/openmaptiles/import-wikidata/builds)
[![](https://img.shields.io/microbadger/layers/openmaptiles/import-wikidata)](https://hub.docker.com/repository/docker/openmaptiles/import-wikidata)
[![](https://img.shields.io/microbadger/image-size/openmaptiles/import-wikidata?label=size)](https://hub.docker.com/repository/docker/openmaptiles/import-wikidata)
[![](https://img.shields.io/docker/pulls/openmaptiles/import-wikidata?label=downloads)](https://hub.docker.com/repository/docker/openmaptiles/import-wikidata)
[![](https://img.shields.io/docker/stars/openmaptiles/import-wikidata?label=stars)](https://hub.docker.com/repository/docker/openmaptiles/import-wikidata)
<br><small>Migrated from [import-wikidata](https://github.com/openmaptiles/import-wikidata) repo (archived)</small>

# Tools

## [generate-osmborder](generate-osmborder)
[![](https://img.shields.io/docker/cloud/build/openmaptiles/generate-osmborder?&logo=OpenStreetMap&label=build)](https://hub.docker.com/repository/docker/openmaptiles/generate-osmborder)
[![](https://img.shields.io/docker/automated/openmaptiles/generate-osmborder?label=build)](https://hub.docker.com/repository/docker/openmaptiles/generate-osmborder/builds)
[![](https://img.shields.io/microbadger/layers/openmaptiles/generate-osmborder)](https://hub.docker.com/repository/docker/openmaptiles/generate-osmborder)
[![](https://img.shields.io/microbadger/image-size/openmaptiles/generate-osmborder?label=size)](https://hub.docker.com/repository/docker/openmaptiles/generate-osmborder)
[![](https://img.shields.io/docker/pulls/openmaptiles/generate-osmborder?label=downloads)](https://hub.docker.com/repository/docker/openmaptiles/generate-osmborder)
[![](https://img.shields.io/docker/stars/openmaptiles/generate-osmborder?label=stars)](https://hub.docker.com/repository/docker/openmaptiles/generate-osmborder)
<br><small>Migrated from [import-osmborder](https://github.com/openmaptiles/import-osmborder) repo, `/generate` dir (archived)</small>

## [generate-vectortiles](generate-vectortiles)
[![](https://img.shields.io/docker/cloud/build/openmaptiles/generate-vectortiles?&logo=OpenStreetMap&label=build)](https://hub.docker.com/repository/docker/openmaptiles/generate-vectortiles)
[![](https://img.shields.io/docker/automated/openmaptiles/generate-vectortiles?label=build)](https://hub.docker.com/repository/docker/openmaptiles/generate-vectortiles/builds)
[![](https://img.shields.io/microbadger/layers/openmaptiles/generate-vectortiles)](https://hub.docker.com/repository/docker/openmaptiles/generate-vectortiles)
[![](https://img.shields.io/microbadger/image-size/openmaptiles/generate-vectortiles?label=size)](https://hub.docker.com/repository/docker/openmaptiles/generate-vectortiles)
[![](https://img.shields.io/docker/pulls/openmaptiles/generate-vectortiles?label=downloads)](https://hub.docker.com/repository/docker/openmaptiles/generate-vectortiles)
[![](https://img.shields.io/docker/stars/openmaptiles/generate-vectortiles?label=stars)](https://hub.docker.com/repository/docker/openmaptiles/generate-vectortiles)
<br><small>Migrated from [generate-vectortiles](https://github.com/openmaptiles/generate-vectortiles) repo (archived)</small>

## [postgis](postgis)
[![](https://img.shields.io/docker/cloud/build/openmaptiles/postgis?&logo=OpenStreetMap&label=build)](https://hub.docker.com/repository/docker/openmaptiles/postgis)
[![](https://img.shields.io/docker/automated/openmaptiles/postgis?label=build)](https://hub.docker.com/repository/docker/openmaptiles/postgis/builds)
[![](https://img.shields.io/microbadger/layers/openmaptiles/postgis)](https://hub.docker.com/repository/docker/openmaptiles/postgis)
[![](https://img.shields.io/microbadger/image-size/openmaptiles/postgis?label=size)](https://hub.docker.com/repository/docker/openmaptiles/postgis)
[![](https://img.shields.io/docker/pulls/openmaptiles/postgis?label=downloads)](https://hub.docker.com/repository/docker/openmaptiles/postgis)
[![](https://img.shields.io/docker/stars/openmaptiles/postgis?label=stars)](https://hub.docker.com/repository/docker/openmaptiles/postgis)
<br><small>Migrated from [postgis](https://github.com/openmaptiles/postgis) repo (archived)</small>
