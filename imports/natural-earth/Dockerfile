# Use a separate docker for downloading to minimize final docker image
FROM openmaptiles/openmaptiles-tools:0.12.0 as downloader
WORKDIR /usr/src/app-ne
COPY clean-natural-earth.sh .
RUN wget --quiet http://naciscdn.org/naturalearth/packages/natural_earth_vector.sqlite.zip && \
    unzip -oj natural_earth_vector.sqlite.zip -d . '*natural_earth_vector.sqlite' && \
    NATURAL_EARTH_DB=./natural_earth_vector.sqlite ./clean-natural-earth.sh


FROM osgeo/gdal:alpine-normal-3.0.2
MAINTAINER "Yuri Astrakhan <YuriAstrakhan@gmail.com>"

ENV IMPORT_DATA_DIR=/import \
    NATURAL_EARTH_DB=/import/natural_earth_vector.sqlite

COPY --from=downloader /usr/src/app-ne/natural_earth_vector.sqlite ${IMPORT_DATA_DIR}/
WORKDIR /usr/src/app
COPY ./import-natural-earth.sh .

CMD ["./import-natural-earth.sh"]
