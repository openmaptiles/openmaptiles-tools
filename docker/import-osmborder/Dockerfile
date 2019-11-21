ARG DOCKER_TAG=latest
FROM openmaptiles/openmaptiles-tools:${DOCKER_TAG}

LABEL maintainer="YuriAstrakhan@gmail.com"

ENV IMPORT_DIR=/import \
    OSM_BORDER_URL=https://github.com/openmaptiles/import-osmborder/releases/download/v0.4/osmborder_lines.csv.gz \
    PGFUTTER_VERSION=1.2

RUN wget --quiet -O /usr/local/bin/pgfutter \
         "https://github.com/lukasmartinelli/pgfutter/releases/download/v$PGFUTTER_VERSION/pgfutter_linux_amd64" \
 && chmod +x /usr/local/bin/pgfutter \
 && mkdir -p "$IMPORT_DIR" \
 && wget --quiet -O "$IMPORT_DIR/osmborder_lines.csv.gz" "$OSM_BORDER_URL" \
 && gzip -d "$IMPORT_DIR/osmborder_lines.csv.gz"

WORKDIR /usr/src/app/
COPY . /usr/src/app/
CMD ["./import_osmborder_lines.sh"]
