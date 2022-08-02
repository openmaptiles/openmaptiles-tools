# PostGIS + OSM-specific extensions Docker image
[![Docker Automated build](https://img.shields.io/docker/automated/openmaptiles/postgis.svg)]()

This images is based on PostgreSQL 14 and PostGIS 3.2 [Docker image](https://hub.docker.com/r/postgis/postgis/) and includes [osml10n extension](https://github.com/openmaptiles/mapnik-german-l10n.git) - OSM-specific label manipulation support.

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
