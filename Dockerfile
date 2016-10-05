FROM debian:jessie
MAINTAINER "Lukas Martinelli <me@lukasmartinelli.ch>"

ENV IMPORT_DATA_DIR=/import \
    NATURAL_EARTH_DB=/import/natural_earth_vector.sqlite

RUN apt-get update && apt-get install -y --no-install-recommends \
      wget \
      unzip \
      gdal-bin \
      sqlite3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app
COPY ./clean-natural-earth.sh /usr/src/app/
RUN wget --quiet http://naciscdn.org/naturalearth/packages/natural_earth_vector.sqlite.zip \
    && unzip -oj natural_earth_vector.sqlite.zip -d /import \
    && rm natural_earth_vector.sqlite.zip \
    && /usr/src/app/clean-natural-earth.sh

COPY . /usr/src/app
CMD ["./import-natural-earth.sh"]
