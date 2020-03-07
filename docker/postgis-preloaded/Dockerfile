FROM openmaptiles/import-lakelines as lakelines
FROM openmaptiles/import-natural-earth as natural-earth
FROM openmaptiles/import-water as water

FROM openmaptiles/postgis

# There is a relevant discussion in
# https://github.com/docker-library/postgres/issues/661#issuecomment-573192715

# Override PGDATA to change the default location of the Postgres data directory
# to another place that has not been created as a volume
ENV  IMPORT_DIR=/import \
     POSTGRES_DB=openmaptiles \
     POSTGRES_USER=openmaptiles \
     POSTGRES_PASSWORD=openmaptiles \
     PGDATA=/var/lib/postgresql/data_no_volume

# switch to postgres user for ownership and execution
USER postgres

COPY --from=lakelines /usr/src/app/import_lakelines.sh /docker-entrypoint-initdb.d/20_import_lakelines.sh
COPY --from=lakelines $IMPORT_DIR/lake_centerline.geojson $IMPORT_DIR/

ENV NATURAL_EARTH_DB=/import/natural_earth_vector.sqlite
COPY --from=natural-earth /usr/src/app/import-natural-earth.sh /docker-entrypoint-initdb.d/30_import-natural-earth.sh
COPY --from=natural-earth $IMPORT_DIR/natural_earth_vector.sqlite $IMPORT_DIR/

ENV IMPORT_DATA_DIR=/import
COPY --from=water /usr/src/app/import-water.sh /docker-entrypoint-initdb.d/40_import-water.sh
COPY --from=water $IMPORT_DIR/* $IMPORT_DIR/

COPY custom-entrypoint.sh /usr/local/bin/

# create custom data dir with ownership to postgres user
RUN mkdir -p "${PGDATA}"

# execute custom entry point to initialize with scripts and build the data dir
RUN custom-entrypoint.sh postgres || exit 0

ENTRYPOINT [ "custom-entrypoint.sh" ]

# using this CMD works so that docker run ... doesnt require a command override,
# only downside is it calls SET for this parameter on every psql issued to the container
CMD [ "-c", "max_locks_per_transaction=512" ]
