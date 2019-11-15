#!/bin/bash

#  Start pgclimb command !   
set -o errexit
set -o pipefail
set -o nounset

max_tries=40
tries=0
while ! pg_isready -q -d $POSTGRES_DB -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER
do
    tries=$((tries + 1))
    if [ $tries -gt $max_tries ]; then
        echo "... Gave up , No connections with :  pg_isready -d $POSTGRES_DB -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER  "
        exit 1  
    fi    
    sleep 2
done

pgclimb --password "$POSTGRES_PASSWORD" \
        --host "$POSTGRES_HOST" \
        --port "$POSTGRES_PORT" \
        --dbname="$POSTGRES_DB" \
        --username="$POSTGRES_USER"  "$@"
