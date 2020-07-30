FROM node:14
MAINTAINER Adam Laza <adam.laza@maptiler.com>

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

RUN npm_config_user=root npm install -g \
        @mapbox/mbtiles \
        @mapbox/tilelive \
        tilelive-pgquery

VOLUME /export
ENV EXPORT_DIR=/export TILELIVE_BIN=tl

COPY . /usr/src/app/
CMD ["/usr/src/app/export-local-pgquery.sh"]
