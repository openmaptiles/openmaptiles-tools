#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

readonly EXPORT_DIR="/export"
readonly RENDER_SCHEME=${RENDER_SCHEME:-pyramid}
readonly MIN_ZOOM=${MIN_ZOOM:-0}
readonly MID_ZOOM=${MID_ZOOM:-12}
readonly MAX_ZOOM=${MAX_ZOOM:-14}
readonly BBOX=${BBOX:-"-180.0,-85.0511,180.0,85.0511"}

PGHOSTS_LIST="host=10.220.44.57&host=10.220.44.56&host=10.220.44.59"  # &host=...&host=...
PGPORT=5432
HOST_COUNT=3  # number of postgres servers
CPU=16  # number of CPUs per postgres server
MAXCONNECTIONS=$(( CPU + CPU / 10 ))
ALL_STREAMS=$(( MAXCONNECTIONS * HOST_COUNT ))

PQGUERY="pgquery://?database=$PGDATABASE&$PGHOSTS_LIST&port=$PGPORT&username=$PGUSER&password=$PGPASSWORD&funcZXY=getmvt&testOnStartup=false&maxpool=$MAXCONNECTIONS"
echo $PQGUERY

function export_local_mbtiles() {
  local mbtiles_name="tiles.mbtiles"
	exec tilelive-copy \
        --scheme=pyramid \
        --retry=2 \
        --bounds="$BBOX" \
        --timeout=1800000 \
        --minzoom="$MIN_ZOOM" \
        --maxzoom="$MAX_ZOOM" \
        --concurrency="$ALL_STREAMS" \
        "$PQGUERY" "mbtiles://$EXPORT_DIR/$mbtiles_name"
}

#echo "Generating zoom from $MIN_ZOOM to $MAX_ZOOM."
echo "Generating zoom $MIN_ZOOM..$MAX_ZOOM from $HOST_COUNT servers, using $MAXCONNECTIONS connections per server, $ALL_STREAMS streams"
export_local_mbtiles
