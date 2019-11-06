#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

readonly PGCONN="dbname=$POSTGRES_DB user=$POSTGRES_USER host=$POSTGRES_HOST password=$POSTGRES_PASSWORD port=$POSTGRES_PORT"

function import_geojson() {
    local geojson_file=$1
    local table_name=$2

    PGCLIENTENCODING=UTF8 ogr2ogr \
    -f Postgresql \
    -s_srs EPSG:4326 \
    -t_srs EPSG:3857 \
    PG:"$PGCONN" \
    "$geojson_file" \
    -nln "$table_name"
}

import_geojson "$IMPORT_DIR/lake_centerline.geojson" "lake_centerline"
