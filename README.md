# Import OpenStreetMap into PostGIS using osm2pgsql and ClearTables

This Docker image will import an OSM PBF file using [osm2pgsql](http://wiki.openstreetmap.org/wiki/Osm2pgsql) and
the [ClearTables osm2pgsql style](https://github.com/ClearTables/ClearTables).

## Usage

### Download PBF File

Use [Geofabrik](http://download.geofabrik.de/index.html) and choose the extract
of your country or region. Download it and put it into the directory.

### Clone ClearTables

Now clone your desired version of [ClearTables](https://github.com/ClearTables/ClearTables).

```bash
git clone https://github.com/ClearTables/ClearTables.git
```

### Import

The **import-osm** Docker container will take the first PBF file in the volume mounted to the `/import` folder and import it using osm2pgsql.
You also need to mount the ClearTables osm2pgsql style you want to use and mount it to `/opt/cleartables`.

```bash
docker run --rm \
    -v ./:/import \
    -v ./:/mapping \
    -e POSTGRES_USER="osm" \
    -e POSTGRES_PASSWORD="osm" \
    -e POSTGRES_HOST="127.0.0.1" \
    -e POSTGRES_DB="osm" \
    -e POSTGRES_PORT="5432" \
    osm2vectortiles/import-osm
```

