# Use a separate docker for downloading and cleanup to minimize final docker image
FROM bash as downloader

# Prepare Natural Earth data from http://www.naturalearthdata.com/
COPY clean-natural-earth.sh /downloads/
RUN set -eux  ;\
    DIR=/downloads/natural_earth  ;\
    mkdir -p "$DIR"  ;\
    cd "$DIR"  ;\
    apk add --no-cache sqlite  ;\
    wget --quiet https://dev.maptiler.download/geodata/omt/natural_earth_vector.sqlite_v5.1.2.zip ;\
    unzip -oj natural_earth_vector.sqlite_v5.1.2.zip  ;\
    ../clean-natural-earth.sh natural_earth_vector.sqlite  ;\
    rm ../clean-natural-earth.sh  ;\
    rm natural_earth_vector.sqlite_v5.1.2.zip

# Download water polygons data from http://osmdata.openstreetmap.de
RUN set -eux  ;\
    DIR=/downloads/water_polygons  ;\
    mkdir -p "$DIR"  ;\
    cd "$DIR"  ;\
    wget --quiet http://osmdata.openstreetmap.de/download/water-polygons-split-3857.zip  ;\
    unzip -oj water-polygons-split-3857.zip  ;\
    rm water-polygons-split-3857.zip

# Download lake centerlines from https://github.com/lukasmartinelli/osm-lakelines
RUN set -eux  ;\
    DIR=/downloads/lake_centerline  ;\
    mkdir -p "$DIR"  ;\
    cd "$DIR"  ;\
    wget --quiet https://dev.maptiler.download/geodata/omt/lake_centerline.geojson


FROM osgeo/gdal:alpine-normal-3.5.1
LABEL maintainer="Yuri Astrakhan <YuriAstrakhan@gmail.com>"

ENV DATA_DIR=/import

COPY --from=downloader /downloads $DATA_DIR/

WORKDIR /usr/src/app
COPY import_data.sh /usr/src/app

CMD ["./import_data.sh"]
