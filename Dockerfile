FROM postgres:9.6
MAINTAINER "Lukas Martinelli <me@lukasmartinelli.ch>"
ENV POSTGIS_MAJOR=2.4dev \
    POSTGIS_VERSION=2.4dev \
    GEOS_VERSION=3.6.0

RUN apt-get -y update \
 && apt-get -y --no-install-recommends install \
        autotools-dev \
        automake \
        autoconf \
        bison \
        curl \
        git \
        libtool \
        libcunit1-dev \
        xsltproc \
        docbook-xsl \
        docbook-mathml \
        dblatex \
        build-essential \
        cmake \
        ca-certificates \
        unzip \
        # PostGIS build dependencies
                postgresql-server-dev-$PG_MAJOR libxml2-dev libjson0-dev libproj-dev libgdal-dev \
 && rm -rf /var/lib/apt/lists/*

RUN cd /opt/ \
 && curl -o /opt/geos.tar.bz2 http://download.osgeo.org/geos/geos-$GEOS_VERSION.tar.bz2 \
 && mkdir /opt/geos \
 && tar xf /opt/geos.tar.bz2 -C /opt/geos --strip-components=1 \
 && cd /opt/geos/ \
 && ./configure \
 && make -j \
 && make install \
 && rm -rf /opt/geos*

RUN cd /opt/ \
 && curl -L https://github.com/google/protobuf/archive/v3.0.2.tar.gz | tar xvz && cd protobuf-3.0.2 \
 && ./autogen.sh \
 && ./configure \
 && make \
 && make install \
 && ldconfig

RUN cd /opt/ \
 && curl -L https://github.com/protobuf-c/protobuf-c/releases/download/v1.2.1/protobuf-c-1.2.1.tar.gz | tar xvz && cd protobuf-c-1.2.1 \
 && ./configure \
 && make \
 && make install \
 && ldconfig

RUN cd /opt/ \
 && git clone -b svn-trunk https://github.com/postgis/postgis.git \
 && cd postgis \
 && git reset --hard a767ba280e73446aa33a32ec253781a2f0da7d67 \
 && ./autogen.sh \
 && ./configure CFLAGS="-O0 -Wall" \
 && make \
 && make install \
 && ldconfig

 ##&& (cd /opt/postgis/extensions/postgis && make -j && make install) \
COPY ./initdb-postgis.sh /docker-entrypoint-initdb.d/10_postgis.sh
