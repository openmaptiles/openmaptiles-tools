#!/usr/bin/env sh
set -o errexit
set -o nounset


# File paths must correspond to the files prepared in Dockerfile
: "${NATURAL_EARTH_FILE:=${DATA_DIR:?}/natural_earth/natural_earth_vector.sqlite}"
: "${WATER_POLYGONS_FILE:=${DATA_DIR:?}/water_polygons/water_polygons.shp}"
: "${LAKE_CENTERLINE_FILE:=${DATA_DIR:?}/lake_centerline/lake_centerline.geojson}"

# These vars define the destination tables when importing
: "${WATER_TABLE_NAME:=osm_ocean_polygon}"
: "${LAKE_CENTERLINE_TABLE:=lake_centerline}"


if [ -z ${PGCONN+x} ]; then
  # For backward compatibility, allow both PG* and POSTGRES_* forms,
  # with the non-standard POSTGRES_* form taking precedence.
  # An error will be raised if neither form is given, except for the PGPORT
  PGHOST="${POSTGRES_HOST:-${PGHOST?}}"
  PGDATABASE="${POSTGRES_DB:-${PGDATABASE?}}"
  PGUSER="${POSTGRES_USER:-${PGUSER?}}"
  PGPASSWORD="${POSTGRES_PASSWORD:-${PGPASSWORD?}}"
  PGPORT="${POSTGRES_PORT:-${PGPORT:-5432}}"

  PGCONN="dbname=$PGDATABASE user=$PGUSER host=$PGHOST password=$PGPASSWORD port=$PGPORT"
  INFO="into $PGHOST:$PGPORT/$PGDATABASE"
else
  INFO="using custom PGCONN env variable"
fi


if [ -z ${1+x} ] || [ "$1" = "natural-earth" ]; then
  echo "Importing Natural Earth $INFO..."
  PGCLIENTENCODING=UTF8 ogr2ogr \
    -progress \
    -f Postgresql \
    -s_srs EPSG:4326 \
    -t_srs EPSG:3857 \
    -clipsrc -180.1 -85.0511 180.1 85.0511 \
    "PG:$PGCONN" \
    -lco GEOMETRY_NAME=geometry \
    -lco OVERWRITE=YES \
    -lco DIM=2 \
    -nlt GEOMETRY \
    -overwrite \
    "${NATURAL_EARTH_FILE:?}"
fi


if [ -z ${1+x} ] || [ "$1" = "water-polygons" ]; then
  echo "Importing $WATER_POLYGONS_FILE as table $WATER_TABLE_NAME $INFO..."
  PGCLIENTENCODING=UTF8 ogr2ogr \
      -progress \
      -f Postgresql \
      -s_srs EPSG:3857 \
      -t_srs EPSG:3857 \
      -lco OVERWRITE=YES \
      -lco GEOMETRY_NAME=geometry \
      -overwrite \
      -nln "$WATER_TABLE_NAME" \
      -nlt geometry \
      --config PG_USE_COPY YES \
      "PG:$PGCONN" \
      "${WATER_POLYGONS_FILE:?}"
fi


if [ -z ${1+x} ] || [ "$1" = "lake-centerline" ]; then
  echo "Importing lake lines as table $LAKE_CENTERLINE_TABLE $INFO..."
  PGCLIENTENCODING=UTF8 ogr2ogr \
    -progress \
    -f Postgresql \
    -s_srs EPSG:4326 \
    -t_srs EPSG:3857 \
    "PG:$PGCONN" \
    -lco OVERWRITE=YES \
    -overwrite \
    -nln "$LAKE_CENTERLINE_TABLE" \
    "${LAKE_CENTERLINE_FILE:?}"
fi
