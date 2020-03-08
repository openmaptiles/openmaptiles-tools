#!/usr/bin/env bash
set -Eeo pipefail

mkdir -p "${PGDATA}"

# This code was adapted from a postgres issue
# https://github.com/docker-library/postgres/issues/661#issuecomment-573192715

source "$(command -v docker-entrypoint.sh)"

docker_setup_env
docker_create_db_directories

docker_verify_minimum_env
docker_init_database_dir
pg_setup_hba_conf

# only required for '--auth[-local]=md5' on POSTGRES_INITDB_ARGS
export PGPASSWORD="${PGPASSWORD:-$POSTGRES_PASSWORD}"

# Support for the import scripts from other docker containers
# Override PGCONN so that ogr2ogr would connect via socket rather than TCP
export PGCONN="dbname=$POSTGRES_DB user=$POSTGRES_USER password=$PGPASSWORD"

docker_temp_server_start -c autovacuum=off
docker_setup_db
docker_process_init_files /docker-entrypoint-initdb.d/*
docker_temp_server_stop
