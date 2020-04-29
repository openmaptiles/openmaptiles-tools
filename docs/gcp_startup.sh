#!/usr/bin/env bash
set -euo pipefail

if (($(id -u) != 0)); then
  echo "***************************************************"
  echo "***  FATAL:  This script should be ran as ROOT  ***"
  echo "***************************************************"
  exit 1
fi

UTF8PROC_TAG=v2.5.0
MAPNIK_GERMAN_L10N_TAG=v2.5.8
PGSQL_GZIP_TAG=v1.0.0

CURL="curl --silent --show-error --location"

# Get configuration metadata (set with --metadata param during VM creation with gcloud)
GET_METADATA="$CURL -H Metadata-Flavor:Google"
PG_VERSION=$($GET_METADATA http://metadata.google.internal/computeMetadata/v1/instance/attributes/pg_version)
OMT_PGDATABASE=$($GET_METADATA http://metadata.google.internal/computeMetadata/v1/instance/attributes/pg_database)
OMT_PGUSER=$($GET_METADATA http://metadata.google.internal/computeMetadata/v1/instance/attributes/pg_user)
OMT_PGPASSWORD=$($GET_METADATA http://metadata.google.internal/computeMetadata/v1/instance/attributes/pg_password)

# PostgreSQL dirs/files updated by this script
# The non-existance of the config file is also used as an indicatior
# that this is the first time this script has ran.
PG_DIR="/etc/postgresql/${PG_VERSION}/main"
PG_CONFIG_FILE="${PG_DIR}/conf.d/99-custom.conf"
PG_HBA_FILE="${PG_DIR}/pg_hba.conf"

if [[ ! -f "${PG_CONFIG_FILE}" ]]; then
  echo "************ First time initialization **************"

  # Add PostgreSQL packages
  $CURL https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
  sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'

  # Install the PostgreSQL server and postgis extension
  DEBIAN_FRONTEND=noninteractive apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y "postgresql-${PG_VERSION}" postgis

  # Install dependencies required to build extensions
  DEBIAN_FRONTEND=noninteractive apt-get install -y "postgresql-server-dev-${PG_VERSION}" build-essential git \
    xsltproc pandoc libkakasi2-dev libgdal-dev libprotobuf-dev libprotobuf-c-dev protobuf-c-compiler libxml2-dev \
    zlib1g-dev bison flex

  # Build and install Postgres extentions
  cd /opt

  echo "Installing utf8proc"
  git clone --branch "$UTF8PROC_TAG" --depth 1 https://github.com/JuliaStrings/utf8proc.git
  cd utf8proc
  make
  make install
  ldconfig
  cd /opt
  rm -rf utf8proc

  echo "Installing mapnik-german-l10n"
  git clone --branch "$MAPNIK_GERMAN_L10N_TAG" --depth 1 https://github.com/giggls/mapnik-german-l10n.git
  cd mapnik-german-l10n
  git checkout -q
  make
  make install
  cd /opt
  rm -rf mapnik-german-l10n

  echo "Installing pgsql-gzip"
  git clone --branch "$PGSQL_GZIP_TAG" --depth 1 https://github.com/pramsey/pgsql-gzip.git
  cd pgsql-gzip
  make
  make install
  cd /opt
  rm -rf pgsql-gzip

  # remove build deps we no longer need
  DEBIAN_FRONTEND=noninteractive apt-get remove --purge -y "postgresql-server-dev-${PG_VERSION}" build-essential git \
    xsltproc pandoc libkakasi2-dev libgdal-dev libprotobuf-dev libprotobuf-c-dev protobuf-c-compiler libxml2-dev \
    zlib1g-dev bison flex

  # Create database
  systemctl restart postgresql
  sleep 3

  sudo -u postgres \
    psql -v ON_ERROR_STOP="1" \
    -c "create user $OMT_PGUSER with password '$OMT_PGPASSWORD'" \
    -c "create database $OMT_PGDATABASE" \
    -c "grant all privileges on database $OMT_PGDATABASE to $OMT_PGUSER" \
    -c "\c $OMT_PGDATABASE" \
    -c "CREATE EXTENSION hstore" \
    -c "CREATE EXTENSION postgis" \
    -c "CREATE EXTENSION unaccent" \
    -c "CREATE EXTENSION fuzzystrmatch" \
    -c "CREATE EXTENSION osml10n" \
    -c "CREATE EXTENSION gzip" \
    -c "CREATE EXTENSION pg_stat_statements"

  # set the firwall rules to allow inbound connections from 10.0.0.0/8
  cat <<EOF | tee "$PG_HBA_FILE"
# DO NOT DISABLE!
# If you change this first entry you will need to make sure that the
# database superuser can access the database using some other method.
# Noninteractive access to all databases is required during automatic
# maintenance (custom daily cronjobs, replication, and similar tasks).
#
# Database administrative login by Unix domain socket
local   all             postgres                                peer

# TYPE  DATABASE        USER            ADDRESS                 METHOD

# "local" is for Unix domain socket connections only
local   all             all                                     peer
# IPv4 local connections:
host    all             all             127.0.0.1/32            md5
# IPv6 local connections:
host    all             all             ::1/128                 md5
# Allow replication connections from localhost, by a user with the
# replication privilege.
local   replication     all                                     peer
host    replication     all             127.0.0.1/32            md5
host    replication     all             ::1/128                 md5

# Allow external connections.
# Note: add here all the networks you want or need.
# Open for all by default with password
host    all     all             10.0.0.0/8            md5

EOF

fi # end of the code that only runs on the first startup

#
# This code should execute on every server restart.
# Recompute available memory and CPU count in case the server
# hardware changed, and adjust Postgres configuration.
# The settings assume this machine is dedicated to Postgres.
#

# Get the current number of CPUs and total memory in MB, used in computations below
CPU_COUNT=$(grep -c ^processor /proc/cpuinfo)
MEM_TOTAL_MB="$(awk '/MemTotal/ { printf "%d", $2/1024 }' /proc/meminfo)"


# %% of the RAM - it should be enough for most of the cases
SHARED_BUFFERS="$(( MEM_TOTAL_MB * 30 / 100 ))MB"

# %% of RAM is assumed to be disk cache (probably more too, but better be conservative)
CACHE_SIZE="$(( MEM_TOTAL_MB * 30 / 100 ))MB"

# if you see one of these errors, raise this value
#  * too many dynamic shared memory segments
#  * remaining connection slots are reserved for non-replication superuser connections
# for low CPU machines (i.e. n1-standard-1), the number should still be sufficiently high.
MAX_CONNECTIONS="$(( 40 + CPU_COUNT * 5 ))"



# this config file will be dynamically generated based on the current machine's resources
cat <<EOF | tee "${PG_CONFIG_FILE}"
#
# THESE VALUES WILL BE REGENERATED ON EVERY MACHINE RESTART
#

    #
    # Resource Consumption
    #

    # https://www.postgresql.org/docs/12/runtime-config-resource.html#GUC-SHARED-BUFFERS
shared_buffers = ${SHARED_BUFFERS}
    # SSD disk has high concurrency
    # https://www.postgresql.org/docs/12/runtime-config-resource.html#GUC-EFFECTIVE-IO-CONCURRENCY
effective_io_concurrency = 300
    # https://www.postgresql.org/docs/12/runtime-config-resource.html#GUC-MAX-PARALLEL-WORKERS-PER-GATHER
max_parallel_workers_per_gather = 8
    # https://www.postgresql.org/docs/12/runtime-config-resource.html#GUC-WORK-MEM
work_mem = 128MB
    # https://www.postgresql.org/docs/12/runtime-config-resource.html#GUC-MAINTENANCE-WORK-MEM
maintenance_work_mem = 256MB

    #
    # Query Planning
    #

    # https://www.postgresql.org/docs/12/runtime-config-query.html#GUC-EFFECTIVE-CACHE-SIZE
effective_cache_size = ${CACHE_SIZE}
    # PostgreSQL 11/12 JIT has a bug making large queries execute 100x slower than without JIT
    # https://www.postgresql.org/docs/12/runtime-config-query.html#GUC-JIT
jit = off
    # https://www.postgresql.org/docs/12/runtime-config-query.html#GUC-RANDOM-PAGE-COST
random_page_cost = 1.0

    #
    # Connections
    #

    # https://www.postgresql.org/docs/12/runtime-config-connection.html#GUC-MAX-CONNECTIONS
max_connections = ${MAX_CONNECTIONS}
    # listen on all interfaces
    # https://www.postgresql.org/docs/12/runtime-config-connection.html#GUC-LISTEN-ADDRESSES
listen_addresses = '*'

    #
    # Write Ahead Log
    #

    # https://www.postgresql.org/docs/12/runtime-config-wal.html#GUC-MIN-WAL-SIZE
min_wal_size = 256MB
    # https://www.postgresql.org/docs/12/runtime-config-wal.html#GUC-MAX-WAL-SIZE
max_wal_size = 50GB
    # https://www.postgresql.org/docs/12/runtime-config-wal.html#GUC-CHECKPOINT-COMPLETION-TARGET
checkpoint_completion_target = 0.8

    #
    # Replication
    #

    # https://www.postgresql.org/docs/12/runtime-config-replication.html#GUC-WAL-KEEP-SEGMENTS
wal_keep_segments = 64
    # https://www.postgresql.org/docs/12/runtime-config-replication.html#GUC-WAL-SENDER-TIMEOUT
wal_sender_timeout = 300s
    # https://www.postgresql.org/docs/12/runtime-config-replication.html#GUC-MAX-WAL-SENDERS
max_wal_senders = 20

EOF

# Set the owner and restart the postgres to pick up the new configuration
chown -R postgres.postgres "$PG_DIR"
systemctl restart postgresql
