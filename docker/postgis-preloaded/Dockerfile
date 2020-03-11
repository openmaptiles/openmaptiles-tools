# To create a clean image, first copy all data and scripts from import-data
# image into builder, and use import it during the docker build phase.
# Next, create an identical postgis-based image and copy resulting PGDATA dir.

# OMT_TOOLS_VERSION will be injected by the dockerhub auto-build environment
ARG OMT_TOOLS_VERSION=latest
FROM openmaptiles/import-data:${OMT_TOOLS_VERSION} as data

ARG OMT_TOOLS_VERSION
RUN echo "**********************************************************" \
 && echo "** Preparing database using openmaptiles/postgis:${OMT_TOOLS_VERSION}..." \
 && echo "**********************************************************"


FROM openmaptiles/postgis:${OMT_TOOLS_VERSION} as builder

# Override PGDATA to change the default location of the Postgres data directory
# to another place that has not been created as a volume
# See also a relevant discussion about data pre-packaging in
# https://github.com/docker-library/postgres/issues/661#issuecomment-573192715

ENV IMPORT_DIR=/import \
    POSTGRES_DB=openmaptiles \
    POSTGRES_USER=openmaptiles \
    POSTGRES_PASSWORD=openmaptiles \
    PGDATA=/var/lib/postgresql/data_no_volume

# NOTE: The ogr2ogr in Debian stable does not support PostgreSQL 12
# Thus parent image must be PG11 or before
RUN DEBIAN_FRONTEND=noninteractive apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        gdal-bin

# switch to postgres user for ownership and execution
USER postgres

# Make sure PGDATA is owned by postgres user
RUN mkdir -p "${PGDATA}"

COPY --from=data $IMPORT_DIR $IMPORT_DIR/
COPY --from=data /usr/src/app/import_data.sh /docker-entrypoint-initdb.d/zz_import_data.sh

COPY preload-database.sh /usr/local/bin/

# initialize and build the data dir
RUN preload-database.sh


# Final image - contains just the resulting PGDATA, without the copy of import-data
ARG OMT_TOOLS_VERSION
FROM openmaptiles/postgis:${OMT_TOOLS_VERSION}

ENV POSTGRES_DB=openmaptiles \
    POSTGRES_USER=openmaptiles \
    POSTGRES_PASSWORD=openmaptiles \
    PGDATA=/var/lib/postgresql/data_no_volume

# switch to postgres user for ownership and execution
USER postgres

# Make sure PGDATA is owned by postgres user
RUN mkdir -p "${PGDATA}"

COPY --from=builder $PGDATA $PGDATA/
