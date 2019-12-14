#!/usr/bin/env sh
set -o errexit
set -o nounset

# For backward compatibility, allow both PG* and POSTGRES_* forms,
# with the non-standard POSTGRES_* form taking precedence.
# An error will be raised if neither form is given, except for the PGPORT
export PGHOST="${POSTGRES_HOST:-${PGHOST?}}"
export PGDATABASE="${POSTGRES_DB:-${PGDATABASE?}}"
export PGUSER="${POSTGRES_USER:-${PGUSER?}}"
export PGPASSWORD="${POSTGRES_PASSWORD:-${PGPASSWORD?}}"
export PGPORT="${POSTGRES_PORT:-${PGPORT:-5432}}"

: "${CSV_FILE:=${IMPORT_DIR?}/osmborder_lines.csv}"
: "${TABLE_NAME:=osm_border_linestring}"


echo "Importing $CSV_FILE into $PGHOST:$PGPORT/$PGDATABASE as table $TABLE_NAME..."

psql -c "DROP TABLE IF EXISTS $TABLE_NAME CASCADE;" \
     -c "CREATE TABLE $TABLE_NAME (osm_id bigint, admin_level int, dividing_line bool, disputed bool, maritime bool, geometry Geometry(LineString, 3857));" \
     -c "CREATE INDEX ON $TABLE_NAME USING gist (geometry);"

pgfutter \
    --schema "public" \
    --host "${PGHOST?}" \
    --port "${PGPORT?}" \
    --dbname "${PGDATABASE?}" \
    --username "${PGUSER?}" \
    --pass "${PGPASSWORD?}" \
    --table "${TABLE_NAME?}" \
csv \
    --fields "osm_id,admin_level,dividing_line,disputed,maritime,geometry" \
    --delimiter "\t" \
"${CSV_FILE?}"
