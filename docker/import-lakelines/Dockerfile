# Use a separate docker for downloading to minimize final docker image
# BASE_TAG will be injected by the dockerhub auto-build environment
ARG BASE_TAG=latest
FROM openmaptiles/openmaptiles-tools:${BASE_TAG} as downloader

WORKDIR /
RUN wget --quiet -L https://github.com/lukasmartinelli/osm-lakelines/releases/download/v0.9/lake_centerline.geojson


FROM osgeo/gdal:alpine-normal-3.0.2
ENV IMPORT_DIR=/import \
    LAKELINES_GEOJSON=/data/import/lake_centerline.geojson

COPY --from=downloader /lake_centerline.geojson $IMPORT_DIR/
WORKDIR /usr/src/app
COPY . /usr/src/app
CMD ["./import_lakelines.sh"]
