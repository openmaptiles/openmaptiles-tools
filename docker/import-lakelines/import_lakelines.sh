#!/usr/bin/env sh
set -o errexit
set -o nounset

LAKE_CENTERLINE_TABLE="${LAKE_CENTERLINE_TABLE:-lake_centerline}"

# For backward compatibility, allow both PG* and POSTGRES_* forms,
# with the non-standard POSTGRES_* form taking precedence.
# An error will be raised if neither form is given, except for the PGPORT
PGHOST="${POSTGRES_HOST:-${PGHOST?}}"
PGDATABASE="${POSTGRES_DB:-${PGDATABASE?}}"
PGUSER="${POSTGRES_USER:-${PGUSER?}}"
PGPASSWORD="${POSTGRES_PASSWORD:-${PGPASSWORD?}}"
PGPORT="${POSTGRES_PORT:-${PGPORT:-5432}}"

PGCONN="${PGCONN:-dbname=$PGDATABASE user=$PGUSER host=$PGHOST password=$PGPASSWORD port=$PGPORT}"

echo "Importing lake lines into PostgreSQL"
PGCLIENTENCODING=UTF8 ogr2ogr \
  -progress \
  -f Postgresql \
  -s_srs EPSG:4326 \
  -t_srs EPSG:3857 \
  PG:"${PGCONN?}" \
  -lco OVERWRITE=YES \
  -overwrite \
  -nln "${LAKE_CENTERLINE_TABLE?}" \
  "$IMPORT_DIR/lake_centerline.geojson"
