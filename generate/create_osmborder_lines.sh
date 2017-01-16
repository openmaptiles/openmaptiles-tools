#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset


function create_borders() {
    local pbf_file="$1"
    local filtered_file="$IMPORT_DIR/filtered.osm.pbf"
    local csv_file="$IMPORT_DIR/osmborder_lines.csv"

    echo "Filter $pbf_file"
    osmborder_filter -o "$filtered_file" "$pbf_file"
    echo "Create border lines in $csv_file"
    osmborder -o "$csv_file" "$filtered_file"
}

function create_borders_with_first_pbf() {
    if [ "$(ls -A $IMPORT_DIR/*.pbf 2> /dev/null)" ]; then
        local pbf_file
        for pbf_file in "$IMPORT_DIR"/*.pbf; do
            create_borders "$pbf_file"
            break
        done
    else
        echo "No PBF files for import found."
        echo "Please mount the $IMPORT_DIR volume to a folder containing OSM PBF files."
        exit 404
    fi
}

create_borders_with_first_pbf
