#!/usr/bin/env bash
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
export EXPIRETILES_ZOOM="${EXPIRETILES_ZOOM:-14}"

function update() {
    imposm run \
        -connection "postgis://$PGUSER:$PGPASSWORD@$PGHOST:$PGPORT/$PGDATABASE" \
        -mapping "$MAPPING_YAML" \
        -cachedir "$IMPOSM_CACHE_DIR" \
        -diffdir "$DIFF_DIR" \
        -expiretiles-dir "$TILES_DIR" \
        -expiretiles-zoom "$EXPIRETILES_ZOOM" \
        -config "$CONFIG_JSON"
}

update
