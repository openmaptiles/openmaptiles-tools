#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

function import_pbf() {
    local pbf="$1"
    local style="$2"
	PGPASSWORD="$POSTGRES_PASSWORD" osm2pgsql \
		--database "$POSTGRES_DB" \
		--user "$POSTGRES_USER" \
		--host "$POSTGRES_HOST" \
		--port "$POSTGRES_PORT" \
		--output multi \
		--style "$style" "$pbf"
}

function exec_psql() {
    PGPASSWORD=$POSTGRES_PASSWORD psql --host="$POSTGRES_HOST" --port="$POSTGRES_PORT"--dbname="$POSTGRES_DB" --username="$POSTGRES_USER"
}

function import_osm() {
    local pbf="$1"
	(cd "$CLEARTABLES_DIR" && make clean && make)
    cat $CLEARTABLES_DIR/sql/types/*.sql | exec_psql
    (cd "$CLEARTABLES_DIR" && import_pbf "$pbf_file" "cleartables.json")
	cat $CLEARTABLES_DIR/sql/post/*.sql | exec_psql
}

function import_osm_with_first_pbf() {
    if [ "$(ls -A $IMPORT_DIR/*.pbf 2> /dev/null)" ]; then
        local pbf_file
        for pbf_file in "$IMPORT_DIR"/*.pbf; do
			import_osm "$pbf_file"
            break
        done
    else
        echo "No PBF files for import found."
        echo "Please mount the $IMPORT_DIR volume to a folder containing OSM PBF files."
        exit 404
    fi
}

import_osm_with_first_pbf
