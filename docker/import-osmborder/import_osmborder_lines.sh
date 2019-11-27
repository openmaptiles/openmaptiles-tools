#!/usr/bin/env bash
set -o errexit
set -o pipefail
set -o nounset

# For backward compatibility, allow both PG* and POSTGRES_* forms,
# with the non-standard POSTGRES_* form taking precedence.
# An error will be raised if neither form is given, except for the PGPORT
export PGHOST="${POSTGRES_HOST:-${PGHOST?}}"
export PGDATABASE="${POSTGRES_DB:-${PGDATABASE?}}"
export PGUSER="${POSTGRES_USER:-${PGUSER?}}"
export PGPASSWORD="${POSTGRES_PASSWORD:-${PGPASSWORD?}}"
export PGPORT="${POSTGRES_PORT:-${PGPORT:-5432}}"


function import_csv() {
    local csv_file="$1"
    local table_name="$2"
    echo "Import CSV file $csv_file"
    pgfutter \
        --schema "public" \
        --host "$PGHOST" \
        --port "$PGPORT" \
        --dbname "$PGDATABASE" \
        --username "$PGUSER" \
        --pass "$PGPASSWORD" \
        --table "$table_name" \
    csv \
        --fields "osm_id,admin_level,dividing_line,disputed,maritime,geometry" \
        --delimiter $'\t' \
    "$csv_file"
}

function drop_table() {
    local table=$1
    local drop_command="DROP TABLE IF EXISTS $table CASCADE;"
    echo "$drop_command" | psql
}

function generalize_border() {
    local target_table_name="$1"
    local source_table_name="$2"
    local tolerance="$3"
    local max_admin_level="$4"
    echo "Generalize $target_table_name with tolerance $tolerance from $source_table_name"
    echo "CREATE TABLE $target_table_name AS SELECT ST_Simplify(geometry, $tolerance) AS geometry, osm_id, admin_level, dividing_line, disputed, maritime FROM $source_table_name WHERE admin_level <= '$max_admin_level';" | psql
    echo "CREATE INDEX ON $target_table_name USING gist (geometry);" | psql
    echo "ANALYZE $target_table_name;" | psql
}

function create_import_table() {
    local target_table_name="$1"
    echo "CREATE TABLE $target_table_name (osm_id bigint, admin_level int, dividing_line bool, disputed bool, maritime bool, geometry Geometry(LineString, 3857));" | psql
    echo "CREATE INDEX ON $target_table_name USING gist (geometry);" | psql
}

function import_borders() {
    local csv_file="$1"
    local table_name="osm_border_linestring"
    drop_table "$table_name"
    echo "Create import table"
    create_import_table "$table_name"
    import_csv "$csv_file" "$table_name"

    local gen_tables="
        osm_border_linestring_gen1,10,10
        osm_border_linestring_gen2,20,10
        osm_border_linestring_gen3,40,8
        osm_border_linestring_gen4,80,6
        osm_border_linestring_gen5,160,6
        osm_border_linestring_gen6,300,4
        osm_border_linestring_gen7,600,4
        osm_border_linestring_gen8,1200,4
        osm_border_linestring_gen9,2400,4
        osm_border_linestring_gen10,4800,2
    "

    for params in $gen_tables; do
        IFS=',' read gen_table_name tolerance max_admin_level <<< "${params}"
        drop_table "$gen_table_name"
        generalize_border "$gen_table_name" "$table_name" $tolerance $max_admin_level &

        if [ ! ${PARALLEL:-0} = 1 ]; then
            wait
        fi
    done

    wait
    echo "Finished border generalization"
}

import_borders "$IMPORT_DIR/osmborder_lines.csv"
