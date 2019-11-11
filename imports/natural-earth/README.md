# Import Natural Earth into PostGIS
[![Docker Automated build](https://img.shields.io/docker/automated/openmaptiles/import-natural-earth.svg?maxAge=2592000)](https://hub.docker.com/r/openmaptiles/import-natural-earth/) [![](https://images.microbadger.com/badges/image/openmaptiles/import-natural-earth.svg)](https://microbadger.com/images/openmaptiles/import-natural-earth)

This is a Docker image to import a subset of [NaturalEarth](http://www.naturalearthdata.com/) using *ogr2ogr* into a PostGIS database.
The SQLite database containing the tables for the import is already baked
into the container to make distribution and execution easier.

## Usage

Provide the database credentials and run `import-natural-earth`.

```bash
docker run --rm -it --net=host \
    -e PGHOST="127.0.0.1" \
    -e PGDATABASE="openmaptiles" \
    -e PGUSER="openmaptiles" \
    -e PGPASSWORD="openmaptiles" \
    openmaptiles/import-natural-earth
```

Optional environment variables:
* `PGPORT` (defaults to `5432`)
* `PGCONN` - Postgres connection string to override all previous env vars

Legacy env variables are still supported, but they are not recommended:
`POSTGRES_HOST`,`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_PORT`

## Natural Earth
Using version [4.1](https://github.com/nvkelso/natural-earth-vector/releases/tag/v4.1.0).
