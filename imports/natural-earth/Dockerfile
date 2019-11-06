FROM openmaptiles/postgis:2.9
MAINTAINER "Lukas Martinelli <me@lukasmartinelli.ch>"

ENV IMPORT_DATA_DIR=/import \
    NATURAL_EARTH_DB=/import/natural_earth_vector.sqlite

WORKDIR /usr/src/app
COPY . /usr/src/app

RUN apt-get update && apt-get install -y --no-install-recommends \
      wget \
      unzip \
      sqlite3 \
    && wget --quiet http://naciscdn.org/naturalearth/packages/natural_earth_vector.sqlite.zip \
    && unzip -oj natural_earth_vector.sqlite.zip -d /import \
    && rm natural_earth_vector.sqlite.zip \
    && /usr/src/app/clean-natural-earth.sh \
    && apt-get purge -y --auto-remove \
      wget \
      unzip \
      sqlite3 \
    && rm -rf /var/lib/apt/lists/*

CMD ["./import-natural-earth.sh"]
