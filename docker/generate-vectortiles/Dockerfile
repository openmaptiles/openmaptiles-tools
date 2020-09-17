FROM node:12
MAINTAINER Lukas Martinelli <me@lukasmartinelli.ch>

# to resolve sqlite3 permission errors
USER node
RUN mkdir -p /home/node/.npm-global ; \
    chown -R node:node /home/node/.npm-global
ENV PATH=/home/node/.npm-global/bin:$PATH
ENV NPM_CONFIG_PREFIX=/home/node/.npm-global

WORKDIR /usr/src/app
RUN npm install -g \
          tl@0.10.2 \
          mapnik@4.5.2 \
          git+https://github.com/mapbox/node-mbtiles.git \
          # bump progress-stream to 2.0.0
          git+https://github.com/smellman/tilelive#debug2 \
          # @mapbox/tilelive@6.1.0 \
          git+https://github.com/smellman/tilelive-tmsource.git#dev-0.9.0b \
          @mapbox/tilelive-vector@4.2.0 \
          @mapbox/tilelive-bridge@3.2.1 \
          git+https://github.com/smellman/tilelive-mapnik#dev-1.1.0

VOLUME /tm2source /export
ENV SOURCE_PROJECT_DIR=/tm2source EXPORT_DIR=/export TILELIVE_BIN=tl

COPY . /usr/src/app/
CMD ["/usr/src/app/export-local.sh"]
