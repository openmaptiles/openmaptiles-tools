# Import Lake Centerlines into PostGIS [![Docker Automated build](https://img.shields.io/docker/automated/openmaptiles/import-lakelines.svg?maxAge=2592000)]()

This is a Docker image to import centered linestrings for labelling OpenStreetMap lakes from the [osm-lakelines](https://github.com/lukasmartinelli/osm-lakelines) repo.
## Usage

Provide the database credentials and run `import-water`.

```bash
docker run --rm \
    -e POSTGRES_USER="osm" \
    -e POSTGRES_PASSWORD="osm" \
    -e POSTGRES_HOST="127.0.0.1" \
    -e POSTGRES_DB="osm" \
    -e POSTGRES_PORT="5432" \
    openmaptiles/import-lakelines
```
