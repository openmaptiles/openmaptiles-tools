#!/bin/bash

#  Start psql command !   

set -o errexit
set -o pipefail
set -o nounset


echo " Connect PostgreSQL ... "
max_tries=40
tries=0
while ! pg_isready -d $POSTGRES_DB -h $POSTGRES_HOST -U $POSTGRES_USER
do
    tries=$((tries + 1))
    if [ $tries -gt $max_tries ]; then
        echo "... Gave up , No connections with :  pg_isready -d $POSTGRES_DB -h $POSTGRES_HOST -U $POSTGRES_USER  "
        exit 1
    else
        echo "$(date) - waiting for PG database to start.  Remained tries=$((max_tries - tries))  Host=$POSTGRES_HOST "    
    fi    
    sleep 2
done


PGPASSWORD="$POSTGRES_PASSWORD" psql \
        --host="$POSTGRES_HOST" \
        --port="$POSTGRES_PORT" \
        --dbname="$POSTGRES_DB" \
        --username="$POSTGRES_USER"  $@
