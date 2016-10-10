#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

readonly PG_CONNECT="postgis://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_HOST/$POSTGRES_DB"


function import_pbf() {
    local pbf_file="$1"
    echo "Importing in diff mode"
    imposm3 import \
        -connection "$PG_CONNECT" \
        -mapping "$MAPPING_YAML" \
        -overwritecache \
        -cachedir "$IMPOSM_CACHE_DIR" \
        -read "$pbf_file" \
        -deployproduction \
        -write -diff
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
