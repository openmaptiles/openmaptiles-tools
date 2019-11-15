FROM openmaptiles/postgis:2.9

ENV VT_UTIL_DIR=/opt/postgis-vt-util \
    VT_UTIL_URL="https://raw.githubusercontent.com/mapbox/postgis-vt-util/v1.0.0/postgis-vt-util.sql" \
    SQL_DIR=/sql

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates \
      wget \
 && mkdir -p "$VT_UTIL_DIR" \
 && wget -P "$VT_UTIL_DIR" --quiet "$VT_UTIL_URL" \
 && apt-get purge -y --auto-remove \
      ca-certificates \
      wget \
 && rm -rf /var/lib/apt/lists/*

VOLUME /sql

COPY . /usr/src/app/
WORKDIR /usr/src/app
CMD ["./import_sql.sh"]
