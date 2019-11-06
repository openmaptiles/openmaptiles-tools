FROM openmaptiles/postgis:2.9
ENV IMPORT_DIR=/import

RUN apt-get update && apt-get install -y --no-install-recommends \
      wget \
      ca-certificates \
 && wget -O pgfutter https://github.com/lukasmartinelli/pgfutter/releases/download/v1.1/pgfutter_linux_amd64 \
 && chmod +x pgfutter \
 && mv pgfutter /usr/local/bin/ \
 && mkdir -p $IMPORT_DIR \
 && wget -O $IMPORT_DIR/osmborder_lines.csv.gz https://github.com/openmaptiles/import-osmborder/releases/download/v0.4/osmborder_lines.csv.gz \
 && gzip -d $IMPORT_DIR/osmborder_lines.csv.gz \
 && apt-get purge -y --auto-remove \
      wget \
      ca-certificates \
 && rm -rf /var/lib/apt/lists/*


WORKDIR /usr/src/app/
COPY . /usr/src/app/
CMD ["./import_osmborder_lines.sh"]
