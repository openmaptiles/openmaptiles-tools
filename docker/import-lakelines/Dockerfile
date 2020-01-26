# Use a separate docker for downloading to minimize final docker image
FROM bash as downloader

WORKDIR /
RUN wget --quiet https://github.com/lukasmartinelli/osm-lakelines/releases/download/v0.9/lake_centerline.geojson


FROM osgeo/gdal:alpine-normal-3.0.2
ENV IMPORT_DIR=/import
ENV LAKELINES_GEOJSON=/data/import/lake_centerline.geojson

COPY --from=downloader /lake_centerline.geojson $IMPORT_DIR/
WORKDIR /usr/src/app
COPY . /usr/src/app
CMD ["./import_lakelines.sh"]
