# PostgreSQL with GEOS 3.6.0 and PostGIS 2.4dev
[![](https://images.microbadger.com/badges/image/openmaptiles/postgis.svg)](https://microbadger.com/images/openmaptiles/postgis "Get your own image badge on microbadger.com") [![Docker Automated buil](https://img.shields.io/docker/automated/openmaptiles/postgis.svg)]()

A custom PostgreSQL Docker image based off GEOS 3.6.0 and PostGIS 2.3.1.

## Usage

Run a PostgreSQL container and mount it to a persistent data directory outside.

In this example we start up the container and create a database `openmaptiles` with the owner `openmaptiles` and password `openmaptiles`
and mount our local directory `./data` as storage.

```bash
docker run \
    -v $(pwd)/data:/var/lib/postgresql/data \
    -e POSTGRES_DB="openmaptiles" \
    -e POSTGRES_USER="openmaptiles" \
    -e POSTGRES_PASSWORD="openmaptiles" \
    -d openmaptiles/postgis
```

### Environment Variables
Unlike all other OpenMapTiles repositories, this repo uses a different set of environment variables to initialize the database - `POSTGRES_*`. See (full documentation](https://hub.docker.com/_/postgres/).

## Build

```bash
docker build -t openmaptiles/postgis .
```
