#!/usr/bin/env sh
set -o errexit
set -o nounset

: "${TABLE_NAME:=osm_ocean_polygon}"
: "${WATER_POLYGONS_FILE:=${IMPORT_DATA_DIR?}/water_polygons.shp}"

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
  echo "Importing $WATER_POLYGONS_FILE into $PGHOST:$PGPORT/$PGDATABASE as table $TABLE_NAME..."
else
  echo "Importing $WATER_POLYGONS_FILE as table $TABLE_NAME using custom PGCONN env variable..."
fi


PGCLIENTENCODING=UTF8 ogr2ogr \
    -progress \
    -f Postgresql \
    -s_srs EPSG:3857 \
    -t_srs EPSG:3857 \
    -lco OVERWRITE=YES \
    -lco GEOMETRY_NAME=geometry \
    -overwrite \
    -nln "$TABLE_NAME" \
    -nlt geometry \
    --config PG_USE_COPY YES \
    "PG:${PGCONN}" \
    "$WATER_POLYGONS_FILE"
