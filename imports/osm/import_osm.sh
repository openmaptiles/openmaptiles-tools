#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

readonly PG_CONNECT="postgis://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_HOST:$POSTGRES_PORT/$POSTGRES_DB"
readonly DIFF_MODE=${DIFF_MODE:-true}


function import_pbf() {
    local pbf_file="$1"
    local diff_flag=""
    if [ "$DIFF_MODE" = true ]; then
        diff_flag="-diff"
        echo "Importing in diff mode"
    else
        echo "Importing in normal mode"
    fi

    imposm3 import \
        -connection "$PG_CONNECT" \
        -mapping "$MAPPING_YAML" \
        -overwritecache \
        -diffdir "$DIFF_DIR" \
        -cachedir "$IMPOSM_CACHE_DIR" \
        -read "$pbf_file" \
        -deployproduction \
        -write $diff_flag
}

function import_osm_with_first_pbf() {
    if [ "$(ls -A $IMPORT_DIR/*.pbf 2> /dev/null)" ]; then
        local pbf_file
        for pbf_file in "$IMPORT_DIR"/*.pbf; do
			import_pbf "$pbf_file"
            break
        done
    else
        echo "No PBF files for import found."
        echo "Please mount the $IMPORT_DIR volume to a folder containing OSM PBF files."
        exit 404
    fi
}

import_osm_with_first_pbf
