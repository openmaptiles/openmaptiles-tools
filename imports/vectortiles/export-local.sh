#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

source utils.sh

readonly RENDER_SCHEME=${RENDER_SCHEME:-pyramid}
readonly MIN_ZOOM=${MIN_ZOOM:-0}
readonly MAX_ZOOM=${MAX_ZOOM:-14}
readonly BBOX=${BBOX:-"-180,-85.0511,180,85.0511"}
readonly COPY_CONCURRENCY=${COPY_CONCURRENCY:-10}
readonly TILE_TIMEOUT=${TILE_TIMEOUT:-1800000}
readonly MBTILES_NAME=${MBTILES_NAME:-tiles.mbtiles}

function export_local_mbtiles() {
    exec tilelive-copy \
        --scheme=pyramid \
        --bounds="$BBOX" \
        --timeout="$TILE_TIMEOUT" \
        --concurrency="$COPY_CONCURRENCY" \
        --minzoom="$MIN_ZOOM" \
        --maxzoom="$MAX_ZOOM" \
        "tmsource://$DEST_PROJECT_DIR" "mbtiles://$EXPORT_DIR/$MBTILES_NAME"
}

function main() {
    copy_source_project
    cleanup_dest_project
    replace_db_connection
    export_local_mbtiles
}

main
