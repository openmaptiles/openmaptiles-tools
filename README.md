# Import OSM into PostGIS using imposm3
[![Docker Automated build](https://img.shields.io/docker/automated/openmaptiles/import-osm.svg)](https://hub.docker.com/r/openmaptiles/import-osm/) [![](https://images.microbadger.com/badges/image/openmaptiles/import-osm.svg)](https://microbadger.com/images/openmaptiles/import-osm "Get your own image badge on microbadger.com")

This Docker image will import an OSM PBF file using [imposm3](https://github.com/omniscale/imposm3) and
a [custom mapping configuration](https://imposm.org/docs/imposm3/latest/mapping.html).

## Usage

### Download PBF File

Use [Geofabrik](http://download.geofabrik.de/index.html) and choose the extract
of your country or region. Download it and put it into the directory.

### Import

The **import-osm** Docker container will take the first PBF file in the volume mounted to the `/import` folder and import it using imposm3 using the mapping file from the `$MAPPING_YAML` (default `/mapping/mapping.yaml`).

Volumes:
 - Mount your PBFs into the `/import` folder
 - Mount your `mapping.yaml` into the `/mapping` folder
 - If you want to use diff mode mount a persistent location to the `/cache` folder for later reuse

```bash
docker run --rm \
    -v $(pwd):/import \
    -v $(pwd):/mapping \
    -e POSTGRES_USER="osm" \
    -e POSTGRES_PASSWORD="osm" \
    -e POSTGRES_HOST="127.0.0.1" \
    -e POSTGRES_DB="osm" \
    -e POSTGRES_PORT="5432" \
    openmaptiles/import-osm
```

