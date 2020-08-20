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

readonly PGHOSTS_LIST=${PGHOSTS_LIST:-"postgres"} # "host=xx.xxx.xxx.xx&host=xx.xxx.xxx.xx&host=xx.xxx.xxx.xx"
readonly PGPORT=${PGPORT:-5432}
readonly HOST_COUNT=${HOST_COUNT:-1}  # number of postgres servers
readonly CPU=${CPU:-1}  # number of CPUs per postgres server
readonly MAXCONNECTIONS=$(( CPU + CPU / 10 ))
readonly ALL_STREAMS=$(( MAXCONNECTIONS * HOST_COUNT ))
readonly SQL_FUNC=${SQL_FUNC:-"getmvt"}

PQGUERY="pgquery://?database=$PGDATABASE&$PGHOSTS_LIST&port=$PGPORT&username=$PGUSER&password=$PGPASSWORD&funcZXY=$SQL_FUNC&testOnStartup=false&maxpool=$MAXCONNECTIONS&nogzip=1&key=true"
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
