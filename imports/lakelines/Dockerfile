FROM openmaptiles/postgis:2.9

ENV IMPORT_DIR=/import \
    LAKELINES_GEOJSON=/data/import/lake_centerline.geojson

RUN apt-get update && apt-get install -y --no-install-recommends \
      wget \
      ca-certificates \
    && wget --quiet -L -P "$IMPORT_DIR" https://github.com/lukasmartinelli/osm-lakelines/releases/download/v0.9/lake_centerline.geojson \
    && apt-get purge -y --auto-remove \
      wget \
      ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

COPY . /usr/src/app
CMD ["./import_lakelines.sh"]
