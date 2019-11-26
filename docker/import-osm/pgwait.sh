#!/usr/bin/env bash

# Wait for Postgres to start using pg_isready

set -o errexit
set -o pipefail
set -o nounset

# For backward compatibility, allow both PG* and POSTGRES_* forms,
# with the non-standard POSTGRES_* form taking precedence.
# An error will be raised if neither form is given, except for the PGPORT
export PGHOST="${POSTGRES_HOST:-${PGHOST?}}"
export PGDATABASE="${POSTGRES_DB:-${PGDATABASE?}}"
export PGUSER="${POSTGRES_USER:-${PGUSER?}}"
export PGPORT="${POSTGRES_PORT:-${PGPORT:-5432}}"

: "${MAX_RETRIES:=40}"  # Maximum number of pg_isready calls
tries=0
while ! pg_isready -q
do
    tries=$((tries + 1))
    if (( tries > MAX_RETRIES )); then
        echo "... gave up waiting for Postgres:   PGHOST=${PGHOST} PGDATABASE=${PGDATABASE} PGUSER=${PGUSER} PGPORT=${PGPORT} pg_isready"
        exit 1
    fi
    sleep 2
done
