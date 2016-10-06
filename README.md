# Export MBTiles from TM2Source

*This is a work in progress towards OSM2VectorTiles v3.0*

A Docker image to export MBTiles (containing gzipped MVT PBF) from a TM2Source project.
The TM2Source project usually references a database you need to link against this container.

## Usage

You need to provide the database credentials and run `export-mbtiles`.

```bash
docker run --rm \
    -v ./osm2vectortiles.tm2source:/tm2source \
    -v ./:/export \
    -e POSTGRES_USER="osm" \
    -e POSTGRES_PASSWORD="osm" \
    -e POSTGRES_HOST="127.0.0.1" \
    -e POSTGRES_DB="osm" \
    -e POSTGRES_PORT="5432" \
    osm2vectortiles/export-mbtiles
```
