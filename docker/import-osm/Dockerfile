FROM golang:1.13-buster
MAINTAINER "Lukas Martinelli <me@lukasmartinelli.ch>"

ENV PG_MAJOR 11
RUN DEBIAN_FRONTEND=noninteractive apt-get update \
 # install newer packages from backports
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      libgeos-dev \
      libleveldb-dev \
      libprotobuf-dev \
      osmctools \
      osmosis \
 # install postgresql client
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      postgresql-client-$PG_MAJOR \
 && ln -s /usr/lib/libgeos_c.so /usr/lib/libgeos.so \
 && rm -rf /var/lib/apt/lists/*

ENV IMPOSM_VERSION 0.8.1

 # add  github.com/julien-noblet/download-geofabrik
RUN go get github.com/julien-noblet/download-geofabrik \
 && go install  github.com/julien-noblet/download-geofabrik \
 && download-geofabrik generate \
 # add  github.com/omniscale/imposm3
 && mkdir -p $GOPATH/src/github.com/omniscale/imposm3 \
 && cd  $GOPATH/src/github.com/omniscale/imposm3 \
 # && git clone --quiet --depth 1 https://github.com/omniscale/imposm3 \
 #
 # update to current omniscale/imposm3
 && git clone --quiet --depth 1 https://github.com/omniscale/imposm3.git -b v$IMPOSM_VERSION \
        $GOPATH/src/github.com/omniscale/imposm3 \
 && make build \
 && mv imposm /usr/bin/imposm \
 # clean
 && rm -rf $GOPATH/bin/godep \
 && rm -rf $GOPATH/src/ \
 && rm -rf $GOPATH/pkg/

VOLUME /import /cache /mapping
ENV IMPORT_DIR=/import \
    IMPOSM_CACHE_DIR=/cache \
    MAPPING_YAML=/mapping/mapping.yaml \
    DIFF_DIR=/import \
    TILES_DIR=/import \
    CONFIG_JSON=config.json

WORKDIR /usr/src/app
COPY . /usr/src/app/
CMD ["./import_osm.sh"]
