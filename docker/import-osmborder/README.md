# Import OSM Borders into PostGIS
[![Docker Automated build](https://img.shields.io/docker/automated/openmaptiles/import-osmborder.svg)](https://hub.docker.com/r/openmaptiles/import-osmborder/) [![](https://images.microbadger.com/badges/image/openmaptiles/import-osmborder.svg)](https://microbadger.com/images/openmaptiles/import-osmborder "Get your own image badge on microbadger.com")

This Docker image will import an OSM PBF file using [imposm3](https://github.com/omniscale/imposm3) and
a [custom mapping configuration](https://imposm.org/docs/imposm3/latest/mapping.html).

## Usage

This docker image uses data created by the **generate-osmborder** image.
The **import-osmborder** will import the embedded CSV into the database.

```bash
docker run --rm \
    -e POSTGRES_USER="osm" \
    -e POSTGRES_PASSWORD="osm" \
    -e POSTGRES_HOST="127.0.0.1" \
    -e POSTGRES_DB="osm" \
    -e POSTGRES_PORT="5432" \
    openmaptiles/import-osmborder
```


## Version of OpenStreetMap
**2017-11-20**
