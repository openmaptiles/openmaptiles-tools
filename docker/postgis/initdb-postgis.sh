#!/usr/bin/env bash
set -o errexit
set -o pipefail
set -o nounset

echo "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
echo "  Loading OMT postgis extensions"
echo "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"

for db in template_postgis "$POSTGRES_DB"; do
echo "Loading extensions into $db"
PGUSER="$POSTGRES_USER" psql --dbname="$db" <<-'EOSQL'
    -- CREATE EXTENSION postgis; -- already loaded by parent docker
    -- CREATE EXTENSION fuzzystrmatch; -- already loaded by parent docker
    CREATE EXTENSION hstore;
    CREATE EXTENSION unaccent;
    CREATE EXTENSION osml10n;
    CREATE EXTENSION gzip;
EOSQL
done
