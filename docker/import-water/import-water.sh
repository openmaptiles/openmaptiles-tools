#!/bin/bash
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

readonly WATER_POLYGONS_FILE="$IMPORT_DATA_DIR/water_polygons.shp"

function import_shp() {
    local shp_file=$1
    local table_name=$2
    shp2pgsql -s 3857 -I -g geometry "$shp_file" "$table_name" | psql | hide_inserts
}

function hide_inserts() {
    grep -v "INSERT 0 1"
}

function drop_table() {
    local table=$1
    local drop_command="DROP TABLE IF EXISTS $table;"
    echo "$drop_command" | psql
}

function generalize_water() {
    local target_table_name="$1"
    local source_table_name="$2"
    local tolerance="$3"
    echo "Generalize $target_table_name with tolerance $tolerance from $source_table_name"
    echo "CREATE TABLE $target_table_name AS SELECT ST_Simplify(geometry, $tolerance) AS geometry FROM $source_table_name" | psql
    echo "CREATE INDEX ON $target_table_name USING gist (geometry)" | psql
    echo "ANALYZE $target_table_name" | psql
}

function import_water() {
    local table_name="osm_ocean_polygon"
    drop_table "$table_name"
    import_shp "$WATER_POLYGONS_FILE" "$table_name"

    local gen1_table_name="osm_ocean_polygon_gen1"
    drop_table "$gen1_table_name"
    generalize_water "$gen1_table_name" "$table_name" 20

    local gen2_table_name="osm_ocean_polygon_gen2"
    drop_table "$gen2_table_name"
    generalize_water "$gen2_table_name" "$table_name" 40

    local gen3_table_name="osm_ocean_polygon_gen3"
    drop_table "$gen3_table_name"
    generalize_water "$gen3_table_name" "$table_name" 80

    local gen4_table_name="osm_ocean_polygon_gen4"
    drop_table "$gen4_table_name"
    generalize_water "$gen4_table_name" "$table_name" 160
}

import_water
