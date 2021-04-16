FROM node:8-slim
LABEL maintainer="Tomas Pohanka <TomPohys@gmail.com>"

WORKDIR /usr/src/app
RUN npm install -g \
          mapnik@3.7.2 \
          @mapbox/mbtiles@0.11.0 \
          @mapbox/tilelive@6.1.0 \
          tilelive-tmsource@0.8.2 \
          --unsafe-perm

VOLUME /tm2source /export
ENV SOURCE_PROJECT_DIR=/tm2source EXPORT_DIR=/export

COPY . /usr/src/app/
CMD ["/usr/src/app/export-local.sh"]
