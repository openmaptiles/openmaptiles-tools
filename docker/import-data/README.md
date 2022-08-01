# Import Prepared Data into PostGIS [![Docker Automated build](https://img.shields.io/docker/automated/openmaptiles/import-data.svg?maxAge=2592000)](https://hub.docker.com/r/openmaptiles/import-data/)

This is a Docker image containing several datasets used in OpenMapTiles project. Prepared data can be imported into PostgreSQL using ogr2ogr utility.

### Lakelines
Centered linestrings for labelling OpenStreetMap lakes from the [osm-lakelines](https://github.com/lukasmartinelli/osm-lakelines) repo.

### Natural Earth
A subset of [NaturalEarth](http://www.naturalearthdata.com/) version [5.1.2](https://github.com/nvkelso/natural-earth-vector/releases/tag/v5.1.2).

### Water polygons
Water polygons from [OpenStreetMapData](http://osmdata.openstreetmap.de/).

## Usage

Provide the database credentials and run `import-data` image.

```bash
docker run --rm --net=host \
    -e PGHOST="127.0.0.1" \
    -e PGDATABASE="openmaptiles" \
    -e PGUSER="openmaptiles" \
    -e PGPASSWORD="openmaptiles" \
    openmaptiles/import-data
```

Optional environment variables:
* `PGPORT` (defaults to `5432`)
* `PGCONN` - Postgres connection string to override all previous env vars
* `LAKE_CENTERLINE_TABLE` (defaults to `lake_centerline`)

Legacy env variables are still supported, but they are not recommended:
`POSTGRES_HOST`,`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_PORT`
