#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset
shopt -s nullglob

function exec_psql_file() {
    local file_name="$1"
    # Allws additional parameters to be passed to psql
    # For example, PSQL_OPTIONS='-a -A' would echo everything and disable output alignment
    # Using eval allows complex cases with quotes, like PSQL_OPTIONS=" -a -c 'select ...' "
    eval "local psql_opts=(${PSQL_OPTIONS:-})"

    echo "Importing $file_name (md5 $(md5sum < "$file_name")  $(wc -l < "$file_name") lines) into Postgres..."

    PGPASSWORD="$POSTGRES_PASSWORD" psql \
        -v ON_ERROR_STOP="1" \
        --host="$POSTGRES_HOST" \
        ${POSTGRES_PORT:+ --port="$POSTGRES_PORT"} \
        --dbname="$POSTGRES_DB" \
        --username="$POSTGRES_USER" \
        -c '\timing on' \
        -f "$file_name" \
        "${psql_opts[@]}"
}

function import_all_sql_files() {
    local dir="$1"
    local sql_file
    for sql_file in "$dir"/*.sql; do
        exec_psql_file "$sql_file"
    done
}

# If there are no arguments, imports everything,
# otherwise the first argument is the name of a file to be imported.
if [[ $# -eq 0 ]]; then
  import_all_sql_files "$OMT_UTIL_DIR"  # import language.sql
  import_all_sql_files "$VT_UTIL_DIR"  # import postgis-vt-util.sql
  import_all_sql_files "$SQL_DIR"  # import compiled tileset.sql
else
  exec_psql_file "$1"
fi
