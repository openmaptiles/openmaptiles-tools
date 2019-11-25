# Generate Vector Tiles from TM2Source
[![Docker Automated build](https://img.shields.io/docker/automated/openmaptiles/generate-vectortiles.svg?maxAge=2592000)]() [![](https://images.microbadger.com/badges/image/openmaptiles/generate-vectortiles.svg)](https://microbadger.com/images/openmaptiles/generate-vectortiles)

A Docker image to export MBTiles (containing gzipped MVT PBF) from a TM2Source project.
The TM2Source project usually references a database you need to link against this container.

## Usage

You need to provide the database credentials and run `generate-vectortiles`.

```bash
docker run --rm \
    -v $(pwd)/project.tm2source:/tm2source \
    -v $(pwd):/export \
    -e PGHOST="127.0.0.1" \
    -e PGDATABASE="openmaptiles" \
    -e PGUSER="openmaptiles" \
    -e PGPASSWORD="openmaptiles" \
    openmaptiles/generate-vectortiles
```

Optional environment variables:
* `PGPORT` (defaults to `5432`)

Legacy env variables are still supported, but they are not recommended:
`POSTGRES_HOST`,`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_PORT`
