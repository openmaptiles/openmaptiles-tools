FROM node:5
MAINTAINER Lukas Martinelli <me@lukasmartinelli.ch>

WORKDIR /usr/src/app
RUN npm install -g \
          tl@0.8.1 \
          mapnik@3.5.13 \
          mbtiles@0.8.2 \
          tilelive@5.12.2 \
          tilelive-tmsource@0.5.0 \
          tilelive-vector@3.9.3 \
          tilelive-bridge@2.3.1 \
          tilelive-mapnik@0.6.18

VOLUME /tm2source /export
ENV SOURCE_PROJECT_DIR=/tm2source EXPORT_DIR=/export TILELIVE_BIN=tl

COPY . /usr/src/app/
CMD ["/usr/src/app/export-local.sh"]
