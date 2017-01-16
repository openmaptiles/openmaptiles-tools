#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

function import_csv() {
    local csv_file="$1"
    local table_name="$2"
    echo "Import CSV file $csv_file"
    pgfutter \
        --schema "public" \
        --host "$POSTGRES_HOST" \
        --port "$POSTGRES_PORT" \
        --dbname "$POSTGRES_DB" \
        --username "$POSTGRES_USER" \
        --pass "$POSTGRES_PASSWORD" \
        --table "$table_name" \
    csv \
        --fields "osm_id,admin_level,disputed,maritime,geometry" \
        --delimiter $'\t' \
    "$csv_file"
}

function exec_psql() {
    PGPASSWORD=$POSTGRES_PASSWORD psql --host="$POSTGRES_HOST" --port="$POSTGRES_PORT"--dbname="$POSTGRES_DB" --username="$POSTGRES_USER"
}

function drop_table() {
    local table=$1
    local drop_command="DROP TABLE IF EXISTS $table CASCADE;"
    echo "$drop_command" | exec_psql
}

function generalize_border() {
    local target_table_name="$1"
    local source_table_name="$2"
    local tolerance="$3"
    echo "Generalize $target_table_name with tolerance $tolerance from $source_table_name"
    echo "CREATE TABLE $target_table_name AS SELECT ST_Simplify(geometry, $tolerance) AS geometry, osm_id, admin_level, disputed, maritime FROM $source_table_name;" | exec_psql
    echo "CREATE INDEX ON $target_table_name USING gist (geometry);" | exec_psql
    echo "ANALYZE $target_table_name;" | exec_psql
}

function create_import_table() {
    local target_table_name="$1"
    echo "CREATE TABLE $target_table_name (osm_id bigint, admin_level int, disputed bool, maritime bool, geometry Geometry(LineString, 3857));" | exec_psql
    echo "CREATE INDEX ON $target_table_name USING gist (geometry);" | exec_psql
}

function import_borders() {
    local csv_file="$1"
    local table_name="osm_border_linestring"
    drop_table "$table_name"
    echo "Create import table"
    create_import_table "$table_name"
    import_csv "$csv_file" "$table_name"

    local gen1_table_name="osm_border_linestring_gen1"
    drop_table "$gen1_table_name"
    generalize_border "$gen1_table_name" "$table_name" 30

    local gen2_table_name="osm_border_linestring_gen2"
    drop_table "$gen2_table_name"
    generalize_border "$gen2_table_name" "$table_name" 60

    local gen3_table_name="osm_border_linestring_gen3"
    drop_table "$gen3_table_name"
    generalize_border "$gen3_table_name" "$table_name" 120

    local gen4_table_name="osm_border_linestring_gen4"
    drop_table "$gen4_table_name"
    generalize_border "$gen4_table_name" "$table_name" 240

    local gen5_table_name="osm_border_linestring_gen5"
    drop_table "$gen5_table_name"
    generalize_border "$gen5_table_name" "$table_name" 480
}

import_borders "$IMPORT_DIR/osmborder_lines.csv"
