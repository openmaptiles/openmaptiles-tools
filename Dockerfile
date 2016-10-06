FROM osm2vectortiles/postgis
MAINTAINER "Lukas Martinelli <me@lukasmartinelli.ch>"

RUN apt-get -y update \
 && apt-get -y --no-install-recommends install \
        git ca-certificates \
        libboost-dev libboost-system-dev \
        libboost-filesystem-dev libexpat1-dev zlib1g-dev \
        libbz2-dev libpq-dev lua5.2 \
        liblua5.2-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/osm2pgsql
RUN git clone https://github.com/openstreetmap/osm2pgsql.git /opt/osm2pgsql \
 && git checkout 0.90.1
RUN mkdir build \
 && (cd build && cmake .. && make && make install)

RUN osm2pgsql --help
