#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

readonly PGCONN="dbname=$POSTGRES_DB user=$POSTGRES_USER host=$POSTGRES_HOST password=$POSTGRES_PASSWORD port=$POSTGRES_PORT"

function import_natural_earth() {
    echo "Importing Natural Earth to PostGIS"
    PGCLIENTENCODING=LATIN1 ogr2ogr \
    -progress \
    -f Postgresql \
    -s_srs EPSG:4326 \
    -t_srs EPSG:3857 \
    -clipsrc -180.1 -85.0511 180.1 85.0511 \
    PG:"$PGCONN" \
    -lco GEOMETRY_NAME=geometry \
    -lco OVERWRITE=YES \
    -lco DIM=2 \
    -nlt GEOMETRY \
    -overwrite \
    "$NATURAL_EARTH_DB"
}

import_natural_earth
