#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

readonly PG_CONNECT="postgis://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_HOST:$POSTGRES_PORT/$POSTGRES_DB"

function update() {
    imposm run \
        -connection "$PG_CONNECT" \
        -mapping "$MAPPING_YAML" \
        -cachedir "$IMPOSM_CACHE_DIR" \
        -diffdir "$DIFF_DIR" \
        -expiretiles-dir "$TILES_DIR" \
        -expiretiles-zoom 14 \
        -config $CONFIG_JSON
}

update
