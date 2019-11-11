#!/bin/sh
set -o errexit
set -o nounset

# For backward compatibility, allow both PG* and POSTGRES_* forms,
# with the non-standard POSTGRES_* form taking precedence.
# An error will be raised if neither form is given, except for the PGPORT
readonly PGHOST="${POSTGRES_HOST:-${PGHOST?}}"
readonly PGDATABASE="${POSTGRES_DB:-${PGDATABASE?}}"
readonly PGUSER="${POSTGRES_USER:-${PGUSER?}}"
readonly PGPASSWORD="${POSTGRES_PASSWORD:-${PGPASSWORD?}}"
readonly PGPORT="${POSTGRES_PORT:-${PGPORT:-5432}}"

readonly PGCONN="${PGCONN:-dbname=$PGDATABASE user=$PGUSER host=$PGHOST password=$PGPASSWORD port=$PGPORT}"

echo "Importing Natural Earth to PostGIS"
PGCLIENTENCODING=LATIN1 ogr2ogr \
  -progress \
  -f Postgresql \
  -s_srs EPSG:4326 \
  -t_srs EPSG:3857 \
  -clipsrc -180.1 -85.0511 180.1 85.0511 \
  PG:"${PGCONN?}" \
  -lco GEOMETRY_NAME=geometry \
  -lco OVERWRITE=YES \
  -lco DIM=2 \
  -nlt GEOMETRY \
  -overwrite \
  "${NATURAL_EARTH_DB?}"
