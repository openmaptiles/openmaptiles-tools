FROM golang:1.8
MAINTAINER "Lukas Martinelli <me@lukasmartinelli.ch>"

ENV PG_MAJOR 9.6
RUN apt-key adv --keyserver ha.pool.sks-keyservers.net --recv-keys B97B0AFCAA1A47F044F244A07FCC7D46ACCC4CF8 \
 && echo 'deb http://apt.postgresql.org/pub/repos/apt/ jessie-pgdg main' $PG_MAJOR > /etc/apt/sources.list.d/pgdg.list \
 && echo 'deb http://httpredir.debian.org/debian jessie-backports main contrib' > /etc/apt/sources.list.d/backports.list \
 && DEBIAN_FRONTEND=noninteractive apt-get update \
 # install newer packages from backports 
 && DEBIAN_FRONTEND=noninteractive apt-get  -t jessie-backports install -y --no-install-recommends \
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

 # add  github.com/julien-noblet/download-geofabrik
RUN go get github.com/julien-noblet/download-geofabrik \
 && go install  github.com/julien-noblet/download-geofabrik \
 && download-geofabrik update \
 # add  github.com/lukasmartinelli/pgclimb
 && go get github.com/lukasmartinelli/pgclimb \
 && go install github.com/lukasmartinelli/pgclimb \
 # add  github.com/osm2vectortiles/imposm3
 && mkdir -p $GOPATH/src/github.com/omniscale/imposm3 \
 && cd  $GOPATH/src/github.com/omniscale/imposm3 \
 && go get github.com/tools/godep \
 # && git clone --quiet --depth 1 https://github.com/omniscale/imposm3 \
 #
 # update to current omniscale/imposm3
 && git clone --quiet --depth 1 https://github.com/openmaptiles/imposm3.git -b v2017-10-18 \
        $GOPATH/src/github.com/omniscale/imposm3 \
 && make build \
 && mv imposm3 /usr/bin/imposm3 \
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
