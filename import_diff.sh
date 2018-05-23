#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

readonly PG_CONNECT="postgis://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_HOST:$POSTGRES_PORT/$POSTGRES_DB"

function import_diff() {
    imposm3 diff \
        -connection "$PG_CONNECT" \
        -mapping "$MAPPING_YAML" \
        -cachedir "$IMPOSM_CACHE_DIR" \
        -diffdir "$IMPORT_DIR" \
        -expiretiles-dir "$IMPORT_DIR" \
        -expiretiles-zoom 14 \
        -config $CONFIG_JSON "$IMPORT_DIR/changes.osc.gz"
}

import_diff
