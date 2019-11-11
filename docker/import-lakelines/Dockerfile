# Use a separate docker for downloading to minimize final docker image
FROM appropriate/curl as downloader
RUN cd / && \
    curl --compressed -OL https://github.com/lukasmartinelli/osm-lakelines/releases/download/v0.9/lake_centerline.geojson

FROM osgeo/gdal:alpine-small-3.0.2
ENV IMPORT_DIR=/import \
    LAKELINES_GEOJSON=/data/import/lake_centerline.geojson

COPY --from=downloader /lake_centerline.geojson $IMPORT_DIR/
WORKDIR /usr/src/app
COPY . /usr/src/app
CMD ["./import_lakelines.sh"]
