FROM openmaptiles/postgis:2.9
ENV IMPORT_DATA_DIR=/import \
    NATURAL_EARTH_DB=/import/natural_earth_vector.sqlite

RUN apt-get update && apt-get install -y --no-install-recommends \
      wget \
      unzip \
      sqlite3 \
      ca-certificates \
    && mkdir -p $IMPORT_DATA_DIR \
    && wget --quiet http://osmdata.openstreetmap.de/download/water-polygons-split-3857.zip \
    && unzip -oj water-polygons-split-3857.zip -d $IMPORT_DATA_DIR \
    && rm water-polygons-split-3857.zip \
    && apt-get -y --auto-remove purge \
      wget \
      unzip \
      sqlite3 \
      ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app
COPY . /usr/src/app
CMD ["./import-water.sh"]
