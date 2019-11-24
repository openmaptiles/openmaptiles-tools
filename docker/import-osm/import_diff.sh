#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

# For backward compatibility, allow both PG* and POSTGRES_* forms,
# with the non-standard POSTGRES_* form taking precedence.
# An error will be raised if neither form is given, except for the PGPORT
export PGHOST="${POSTGRES_HOST:-${PGHOST?}}"
export PGDATABASE="${POSTGRES_DB:-${PGDATABASE?}}"
export PGUSER="${POSTGRES_USER:-${PGUSER?}}"
export PGPASSWORD="${POSTGRES_PASSWORD:-${PGPASSWORD?}}"
export PGPORT="${POSTGRES_PORT:-${PGPORT:-5432}}"


function import_diff() {
    imposm diff \
        -connection "postgis://$PGUSER:$PGPASSWORD@$PGHOST:$PGPORT/$PGDATABASE" \
        -mapping "$MAPPING_YAML" \
        -cachedir "$IMPOSM_CACHE_DIR" \
        -diffdir "$IMPORT_DIR" \
        -expiretiles-dir "$IMPORT_DIR" \
        -expiretiles-zoom 14 \
        -config "$CONFIG_JSON" \
        "$IMPORT_DIR/changes.osc.gz"
}

import_diff
