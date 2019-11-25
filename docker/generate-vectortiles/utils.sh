#!/bin/bash
set -o errexit
set -o pipefail

readonly DEST_PROJECT_DIR="/tmp/project"
readonly DEST_PROJECT_FILE="${DEST_PROJECT_DIR%%/}/data.yml"

# For backward compatibility, allow both PG* and POSTGRES_* forms,
# with the non-standard POSTGRES_* form taking precedence.
# An error will be raised if neither form is given, except for the PGPORT
PGHOST="${POSTGRES_HOST:-${PGHOST?}}"
PGDATABASE="${POSTGRES_DB:-${PGDATABASE?}}"
PGUSER="${POSTGRES_USER:-${PGUSER?}}"
PGPASSWORD="${POSTGRES_PASSWORD:-${PGPASSWORD?}}"
PGPORT="${POSTGRES_PORT:-${PGPORT:-5432}}"

# project config will be copied to new folder because we
# modify the source configuration
function copy_source_project() {
    cp -rf "$SOURCE_PROJECT_DIR" "$DEST_PROJECT_DIR"
}

# project.yml is single source of truth, therefore the mapnik
# stylesheet is not necessary
function cleanup_dest_project() {
    rm -f "${DEST_PROJECT_DIR%%/}/project.xml"
}

# replace database connection with postgis container connection
function replace_db_connection() {
    local replace_expr_1="s|host: .*|host: \"$PGHOST\"|g"
    local replace_expr_2="s|port: .*|port: \"$PGPORT\"|g"
    local replace_expr_3="s|dbname: .*|dbname: \"$PGDATABASE\"|g"
    local replace_expr_4="s|user: .*|user: \"$PGUSER\"|g"
    local replace_expr_5="s|password: .*|password: \"$PGPASSWORD\"|g"

    sed -i "$replace_expr_1" "$DEST_PROJECT_FILE"
    sed -i "$replace_expr_2" "$DEST_PROJECT_FILE"
    sed -i "$replace_expr_3" "$DEST_PROJECT_FILE"
    sed -i "$replace_expr_4" "$DEST_PROJECT_FILE"
    sed -i "$replace_expr_5" "$DEST_PROJECT_FILE"
}
