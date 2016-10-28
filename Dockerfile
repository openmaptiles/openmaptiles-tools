FROM debian:jessie

ENV IMPORT_DIR=/import \
    LAKELINES_GEOJSON=/data/import/lake_centerline.geojson

RUN apt-get update && apt-get install -y --no-install-recommends \
      wget \
      gdal-bin \
      ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app
RUN wget --quiet -L -P "$IMPORT_DIR" https://github.com/lukasmartinelli/osm-lakelines/releases/download/v0.9/lake_centerline.geojson

COPY . /usr/src/app
CMD ["./import_lakelines.sh"]
