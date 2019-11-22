FROM golang:1.13-buster
LABEL maintainer="YuriAstrakhan@gmail.com"

ARG PG_MAJOR="11"

# By default for now use custom build until we verify everything is stable
ARG IMPOSM_REPO="https://github.com/openmaptiles/imposm3.git"
ARG IMPOSM_VERSION="v2017-10-18"

# Current version, disable for now
#ARG IMPOSM_REPO="https://github.com/omniscale/imposm3.git"
#ARG IMPOSM_VERSION="v0.8.1"


ENV IMPORT_DIR=/import \
    IMPOSM_CACHE_DIR=/cache \
    MAPPING_YAML=/mapping/mapping.yaml \
    DIFF_DIR=/import \
    TILES_DIR=/import \
    CONFIG_JSON=config.json


RUN DEBIAN_FRONTEND=noninteractive apt-get update \
 #
 # install newer packages from backports
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      libgeos-dev \
      libleveldb-dev \
      libprotobuf-dev \
      osmctools \
      osmosis \
      # install postgresql client
      postgresql-client-$PG_MAJOR \
 #
 && ln -s /usr/lib/libgeos_c.so /usr/lib/libgeos.so \
 && rm -rf /var/lib/apt/lists/* \
 #
 # add  github.com/julien-noblet/download-geofabrik
 && go get github.com/julien-noblet/download-geofabrik \
 && go install github.com/julien-noblet/download-geofabrik \
 && download-geofabrik generate \
 #
 # add  github.com/osm2vectortiles/imposm3
 && mkdir -p $GOPATH/src/github.com/omniscale/imposm3 \
 && cd  $GOPATH/src/github.com/omniscale/imposm3 \
 && go get github.com/tools/godep \
 #
 # get and build specific version of imposm
 && git clone --quiet --depth 1 $IMPOSM_REPO -b $IMPOSM_VERSION \
        $GOPATH/src/github.com/omniscale/imposm3 \
 && make build \
 #
 # Support legacy imposm3 as well as the newer imposm app name
 && ( [ -f imposm ] && mv imposm /usr/bin/imposm || mv imposm3 /usr/bin/imposm ) \
 && ln -s /usr/bin/imposm /usr/bin/imposm3 \
 #
 # clean
 && rm -rf $GOPATH/bin/godep \
 && rm -rf $GOPATH/src/ \
 && rm -rf $GOPATH/pkg/

VOLUME /import /cache /mapping
WORKDIR /usr/src/app
COPY . /usr/src/app/
CMD ["./import_osm.sh"]
