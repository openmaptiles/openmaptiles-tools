#!/usr/bin/env bash
set -e

echo "$@"
echo "-----------------------start"
cp /omt/test-sql/test-sql.sh /docker-entrypoint-initdb.d/zzzzzzzzzzzzzzzzzzz.sh
docker-entrypoint.sh postgres
echo "-----------------------end"
