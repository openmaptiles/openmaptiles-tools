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

    # shellcheck disable=SC2154
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

    if [[ -d "$dir/parallel" ]]; then
      # Asseme this dir may contain run_first.sql, parallel/*.sql, and run_last.sql
      # use parallel execution
      if [[ -f "$dir/run_first.sql" ]]; then
        exec_psql_file "$dir/run_first.sql"
      else
        echo "File $dir/run_first.sql not found, skipping"
      fi

      # Run import_sql script in parallel, up to MAX_PARALLEL_PSQL processes at the same time
      : "${MAX_PARALLEL_PSQL:=5}"
      echo "Importing $(find "$dir/parallel" -name "*.sql" | wc -l) sql files from $dir/parallel/, up to $MAX_PARALLEL_PSQL files at the same time"
      find "$dir/parallel" -name "*.sql" -print0 | xargs -0 -I{} -P "$MAX_PARALLEL_PSQL" "$0" "{}"
      echo "Finished importing sql files matching '$dir/parallel/*.sql'"

      if [[ -f "$dir/run_last.sql" ]]; then
        exec_psql_file "$dir/run_last.sql"
      else
        echo "File $dir/run_last.sql not found, skipping"
      fi
    else
      for sql_file in "$dir"/*.sql; do
        exec_psql_file "$sql_file"
      done
    fi
}

# If there are no arguments, imports everything,
# otherwise the first argument is the name of a file to be imported.
if [[ $# -eq 0 ]]; then
  if [[ "${OMT_UTIL_DIR:-}" == "" ]]; then
    echo "ENV variable OMT_UTIL_DIR is not set. It should contain directory with .sql files, e.g. language.sql "
    exit 1
  fi
  if [[ "${VT_UTIL_DIR:-}" == "" ]]; then
    echo "ENV variable VT_UTIL_DIR is not set. It should contain directory with .sql files, e.g. postgis-vt-util.sql"
    exit 1
  fi
  if [[ "${SQL_DIR:-}" == "" ]]; then
    echo "ENV variable SQL_DIR is not set. It should contain directory with .sql files, e.g. tileset.sql, or run_first.sql, run_last.sql, and parallel/*.sql"
    exit 1
  fi

  import_all_sql_files "$OMT_UTIL_DIR"  # import language.sql
  import_all_sql_files "$VT_UTIL_DIR"  # import postgis-vt-util.sql and TileBBox.sql
  import_all_sql_files "$SQL_DIR"  # import compiled tileset.sql
else
  exec_psql_file "$1"
fi
