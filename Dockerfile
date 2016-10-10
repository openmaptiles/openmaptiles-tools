FROM golang:1.7
MAINTAINER "Lukas Martinelli <me@lukasmartinelli.ch>"

RUN DEBIAN_FRONTEND=noninteractive apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      libprotobuf-dev \
      libleveldb-dev \
      libgeos-dev \
      postgresql-client \
      osmctools \
      --no-install-recommends \
 && ln -s /usr/lib/libgeos_c.so /usr/lib/libgeos.so \
 && rm -rf /var/lib/apt/lists/*

WORKDIR $GOPATH/src/github.com/omniscale/imposm3
RUN go get github.com/tools/godep \
 && git clone https://github.com/osm2vectortiles/imposm3 \
        $GOPATH/src/github.com/omniscale/imposm3 \
 && go get \
 && go install

VOLUME /import /cache /mapping
ENV IMPORT_DIR=/import \
    IMPOSM_CACHE_DIR=/cache \
    MAPPING_YAML=/mapping/mapping.yaml

WORKDIR /usr/src/app
COPY . /usr/src/app/
CMD ["./import_osm.sh"]
