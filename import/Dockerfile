FROM openmaptiles/postgis:2.3
ENV IMPORT_DIR=/import

RUN apt-get update && apt-get install -y --no-install-recommends \
      wget \
      unzip \
      sqlite3 \
      ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN wget -O pgfutter https://github.com/lukasmartinelli/pgfutter/releases/download/v1.1/pgfutter_linux_amd64 \
 && chmod +x pgfutter \
 && mv pgfutter /usr/local/bin/

RUN mkdir -p $IMPORT_DIR \
    && wget -O $IMPORT_DIR/osmborder_lines.csv https://github.com/openmaptiles/import-osmborder/releases/download/v0.1/osmborder_lines.csv

WORKDIR /usr/src/app/
COPY . /usr/src/app/
CMD ["./import_osmborder_lines.sh"]
