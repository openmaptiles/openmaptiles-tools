#!/usr/bin/env bash
set -e

# assumes the /omt is mapped to the root of the openmaptiles-tools repo

export PGHOST="${POSTGRES_HOST:-${PGHOST?}}"
export PGDATABASE="${POSTGRES_DB:-${PGDATABASE?}}"
export PGUSER="${POSTGRES_USER:-${PGUSER?}}"
export PGPASSWORD="${POSTGRES_PASSWORD:-${PGPASSWORD?}}"
export PGPORT="${POSTGRES_PORT:-${PGPORT:-5432}}"

MAX_RETRIES=40  # Maximum number of pg_isready calls
tries=0
while ! pg_isready
do
    tries=$((tries + 1))
    if (( tries > MAX_RETRIES )); then
        exit 1
    fi
    sleep 2
done

sleep 1

# Import all pre-required SQL code
source import-sql

echo "++++++++++++++++++++++++"
echo "Running OMT SQL tests"
echo "++++++++++++++++++++++++"

for sql_file in /omt/tests/sql/*.sql; do
  # Ensure output file can be deleted though it is owned by root
  out_file="/omt/build/$(basename "$sql_file").out"
  truncate --size 0 "$out_file"
  chmod 666 "$out_file"
  echo "Executing $sql_file and recording results in $out_file"
  psql -v ON_ERROR_STOP=1 --file "$sql_file" >> "$out_file"
done


echo "++++++++++++++++++++++++"
echo "Running import-borders tests"
echo "++++++++++++++++++++++++"

BORDERS_OUT=/omt/build/import-borders.csv

echo "++++++ Parsing PBF file into CSV..."
BORDERS_CSV_FILE=$BORDERS_OUT /omt/bin/import-borders parse /omt/tests/http/monaco-20150428.osm.pbf
echo "++++++ Load parsed CSV file into a table"
/omt/bin/import-borders load "$BORDERS_OUT"
echo "++++++ Importing a PBF file into a DB table"
/omt/bin/import-borders import /omt/tests/http/monaco-20150428.osm.pbf
echo "++++++ Importing a PBF file into a DB table without import command"
/omt/bin/import-borders /omt/tests/http/monaco-20150428.osm.pbf
echo "++++++ Importing a PBF file into a DB table by scanning a dir"
PBF_DATA_DIR=/omt/tests/http /omt/bin/import-borders


echo "++++++++++++++++++++++++"
echo "Running python tests"
echo "++++++++++++++++++++++++"

python -m unittest discover 2>&1 | \
	awk -v s="Ran 0 tests in" '$$0~s{print; print "\n*** No Python unit tests found, aborting"; exit(1)} 1'

echo "Done with the testing"
