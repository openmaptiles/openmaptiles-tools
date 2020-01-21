#!/usr/bin/env bash
set -e

echo "++++++++++++++++++++++++"
echo "Importing /sql dir"
echo "++++++++++++++++++++++++"
for sql_file in /omt/sql/*.sql; do
  echo "Importing $sql_file..."
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --file "$sql_file"
done

echo "++++++++++++++++++++++++"
echo "Running OMT SQL tests"
echo "++++++++++++++++++++++++"

for sql_file in /omt/test-sql/*.sql; do
  # Ensure output file can be deleted though it is owned by root
  out_file="/omt/build/$(basename "$sql_file").out"
  truncate --size 0 "$out_file"
  chmod 666 "$out_file"
  echo "Executing $sql_file and recording results in $out_file"
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --file "$sql_file" >> "$out_file"
done


echo "Done with the testing"
# Stopping PostgreSQL by intentionally exiting with an error
exit 1
