#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

readonly EXPORT_DIR="/export"
readonly RENDER_SCHEME=${RENDER_SCHEME:-pyramid}
readonly MIN_ZOOM=${MIN_ZOOM:-0}
readonly MAX_ZOOM=${MAX_ZOOM:-10}
readonly COPY_CONCURRENCY=${COPY_CONCURRENCY:-20}
readonly BBOX=${BBOX:-"-180.0,-85.0511,180.0,85.0511"}
FUNCZXY="gettile"

PQGUERY="pgquery://?database=$PGDATABASE&host=postgres&username=$PGUSER&password=$PGPASSWORD&funcZXY=$FUNCZXY&testOnStartup=false&name=swisstopo"
echo $PQGUERY

function export_local_mbtiles() {
  local mbtiles_name="tiles.mbtiles"
	exec tilelive-copy \
        --scheme=pyramid \
        --bounds="$BBOX" \
        --timeout=1800000 \
        --minzoom="$MIN_ZOOM" \
        --maxzoom="$MAX_ZOOM" \
        --concurrency="$COPY_CONCURRENCY" \
        "$PQGUERY" "mbtiles://$EXPORT_DIR/$mbtiles_name"
}

echo "Generating zoom from $MIN_ZOOM to $MAX_ZOOM."
export_local_mbtiles
