#!/usr/bin/env bash
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

# Fix Mapnik output and errors
#
# Usage:
#   filter_deprecation tilelive-copy ...
#
function filter_deprecation()(
  set -e
  if [[ -z "${FILTER_MAPNIK_OUTPUT:-}" ]]; then
    # if FILTER_MAPNIK_OUTPUT is not set, execute as is, without any filtering
    echo "Set FILTER_MAPNIK_OUTPUT=1 to hide deprecation warnings"
    "$@"
    return 0
  fi

  echo "Filtering deprecation warnings from the Mapnik's output."
  (
    # Swap stdin and stderr
    "$@" 3>&2- 2>&1- 1>&3- | (
      # Remove "is deprecated" error messages
      sed -u "/is deprecated/d"
  # Swap back stdin and stderr
  )) 3>&2- 2>&1- 1>&3- | \
  # Fix time precision
  sed -u "s/s\] /000&/;s/\(\.[0-9][0-9][0-9]\)[0-9]*s\] /\1s] /" | \
  # Redraw progress on the same line
  while read line; do
  if [[ "$line" == *left ]] ; then
    echo -n "$line"
  else
    echo "$line"
  fi
done
);
