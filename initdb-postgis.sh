#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

PGUSER="$POSTGRES_USER" psql --dbname="$POSTGRES_DB" <<-'EOSQL'
    CREATE DATABASE template_postgis;
    UPDATE pg_database SET datistemplate = TRUE WHERE datname = 'template_postgis';
EOSQL

for db in template_postgis "$POSTGRES_DB"; do
PGUSER="$POSTGRES_USER" psql --dbname="$db" <<-'EOSQL'
    CREATE EXTENSION postgis;
    CREATE EXTENSION hstore;
    CREATE EXTENSION unaccent;
    CREATE EXTENSION fuzzystrmatch;
    CREATE EXTENSION osml10n;
EOSQL
done
