# Import OSM Borders into PostGIS
[![Docker Automated build](https://img.shields.io/docker/automated/openmaptiles/import-osmborder.svg)](https://hub.docker.com/r/openmaptiles/import-osmborder/) [![](https://images.microbadger.com/badges/image/openmaptiles/import-osmborder.svg)](https://microbadger.com/images/openmaptiles/import-osmborder "Get your own image badge on microbadger.com")

This Docker image will import an OSM PBF file using [imposm3](https://github.com/omniscale/imposm3) and
a [custom mapping configuration](https://imposm.org/docs/imposm3/latest/mapping.html).

## Usage

The process is split into tow steps

1. **generate-osmborder**: Generate a CSV file containing the geometries
2. **import-osmborder**: Docker image containing the CSV file for easy import into PostGIS

### Download PBF File

Use [Geofabrik](http://download.geofabrik.de/index.html) and choose the extract
of your country or region. Download it and put it into the directory.

### Generate

The **generate-osmborder** Docker container will take the first PBF file and generate the CSV file.
Mount your PBFs into the `/import` folder


```bash
docker run --rm \
    -v $(pwd):/import \
    openmaptiles/generate-osmborder
```

Now upload the generated CSV to GitHub releases and update the reference link inside **import-osmborder**.

### Import

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
