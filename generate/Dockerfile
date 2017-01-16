FROM debian:jessie

RUN apt-key adv --keyserver ha.pool.sks-keyservers.net --recv-keys B97B0AFCAA1A47F044F244A07FCC7D46ACCC4CF8 \
 && echo 'deb http://apt.postgresql.org/pub/repos/apt/ jessie-pgdg main' $PG_MAJOR > /etc/apt/sources.list.d/pgdg.list \
 && echo 'deb http://httpredir.debian.org/debian jessie-backports main contrib' > /etc/apt/sources.list.d/backports.list \
 && DEBIAN_FRONTEND=noninteractive apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get  -t jessie-backports install -y --no-install-recommends \
    build-essential \
    zlib1g-dev \
    cmake \
    libosmium2-dev \
    git \
    postgresql-client \
    wget \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/pnorman/osmborder.git /usr/src/osmborder
WORKDIR /usr/src/osmborder/build
RUN cmake .. && make && make install

ENV IMPORT_DIR=/import
VOLUME /import

WORKDIR /usr/src/osmborder
COPY create_osmborder_lines.sh /usr/src/osmborder
CMD ["./create_osmborder_lines.sh"]
