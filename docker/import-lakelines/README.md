# Import Lake Centerlines into PostGIS [![Docker Automated build](https://img.shields.io/docker/automated/openmaptiles/import-lakelines.svg?maxAge=2592000)](https://hub.docker.com/r/openmaptiles/import-lakelines/)

This is a Docker image to import centered linestrings for labelling OpenStreetMap lakes from the [osm-lakelines](https://github.com/lukasmartinelli/osm-lakelines) repo.
## Usage

Provide the database credentials and run `import-lakelines`.

```bash
docker run --rm \
    -e PGHOST="127.0.0.1" \
    -e PGDATABASE="openmaptiles" \
    -e PGUSER="openmaptiles" \
    -e PGPASSWORD="openmaptiles" \
    openmaptiles/import-lakelines
```

Optional environment variables:
* `PGPORT` (defaults to `5432`)
* `LAKE_CENTERLINE_TABLE` (defaults to `lake_centerline`)
* `PGCONN` - Postgres connection string to override all previous env vars

Legacy env variables are still supported, but they are not recommended:
`POSTGRES_HOST`,`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_PORT`
