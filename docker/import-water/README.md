# Import Water from OpenStreetMapData into PostGIS
[![Docker Automated build](https://img.shields.io/docker/automated/openmaptiles/import-water.svg?maxAge=2592000)](https://hub.docker.com/r/openmaptiles/import-water) [![](https://images.microbadger.com/badges/image/openmaptiles/import-water.svg)](https://microbadger.com/images/openmaptiles/import-water)

This is a Docker image to import and simplify water polygons from [OpenStreetMapData](http://osmdata.openstreetmap.de/) using *shp2pgsql* into a PostGIS database.
The Shapefiles are already baked into the container to make distribution and execution easier.

## Usage

Provide the database credentials and run `import-water`.

```bash
docker run --rm \
    -e PGHOST="127.0.0.1" \
    -e PGDATABASE="openmaptiles" \
    -e PGUSER="openmaptiles" \
    -e PGPASSWORD="openmaptiles" \
    openmaptiles/import-water
```
## Version of OpenStreetMapData
**2019-10-28**
