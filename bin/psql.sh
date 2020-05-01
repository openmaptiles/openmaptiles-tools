#!/usr/bin/env bash

#  Start psql command !

set -o errexit
set -o pipefail
set -o nounset

# wait for Postgres. On error, this script will exit too
SOURCE_DIR="$(dirname "$(readlink -f "$0")")"
# shellcheck source=./pgwait
source "$SOURCE_DIR/pgwait"

# For backward compatibility, allow both PG* and POSTGRES_* forms,
# with the non-standard POSTGRES_* form taking precedence.
# An error will be raised if neither form is given, except for the PGPORT
export PGHOST="${POSTGRES_HOST:-${PGHOST?}}"
export PGDATABASE="${POSTGRES_DB:-${PGDATABASE?}}"
export PGUSER="${POSTGRES_USER:-${PGUSER?}}"
export PGPASSWORD="${POSTGRES_PASSWORD:-${PGPASSWORD?}}"
export PGPORT="${POSTGRES_PORT:-${PGPORT:-5432}}"

psql "$@"
