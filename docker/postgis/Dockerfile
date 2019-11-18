FROM postgres:9.6
MAINTAINER "Lukas Martinelli <me@lukasmartinelli.ch>"
ENV POSTGIS_MAJOR=2.4dev \
    POSTGIS_VERSION=2.4dev \
    GEOS_VERSION=3.6.0

RUN apt-get -qq -y update \
 && apt-get -qq -y --no-install-recommends install \
        autoconf \
        automake \
        autotools-dev \
        build-essential \
        ca-certificates \
        bison \
        cmake \
        curl \
        dblatex \
        docbook-mathml \
        docbook-xsl \
        git \
        gdal-bin \
        libcunit1-dev \
        libkakasi2-dev \
        libtool \
        pandoc \
        unzip \
        xsltproc \
        # PostGIS build dependencies
            libgdal-dev \
            libjson0-dev \
            libproj-dev \
            libxml2-dev \
            postgresql-server-dev-$PG_MAJOR \
## GEOS
 && cd /opt/ \
 && curl -o /opt/geos.tar.bz2 http://download.osgeo.org/geos/geos-$GEOS_VERSION.tar.bz2 \
 && mkdir /opt/geos \
 && tar xf /opt/geos.tar.bz2 -C /opt/geos --strip-components=1 \
 && cd /opt/geos/ \
 && ./configure \
 && make -j \
 && make install \
 && rm -rf /opt/geos* \
## Protobuf
 && cd /opt/ \
 && curl -L https://github.com/google/protobuf/archive/v3.0.2.tar.gz | tar xvz && cd protobuf-3.0.2 \
 && ./autogen.sh \
 && ./configure \
 && make \
 && make install \
 && ldconfig \
 && rm -rf /opt/protobuf-3.0.2 \
## Protobuf-c
 && cd /opt/ \
 && curl -L https://github.com/protobuf-c/protobuf-c/releases/download/v1.2.1/protobuf-c-1.2.1.tar.gz | tar xvz && cd protobuf-c-1.2.1 \
 && ./configure \
 && make \
 && make install \
 && ldconfig \
 && rm -rf /opt/protobuf-c.1.2.1 \
## Postgis
 && cd /opt/ \
 && git clone -b svn-trunk https://github.com/postgis/postgis.git \  
 && cd postgis \
 && git reset --hard ff0a844e606622f45841fc25221bbaa136ed1001 \ 
 && ./autogen.sh \
 && ./configure CFLAGS="-O0 -Wall" \
 && make \
 && make install \
 && ldconfig \
 && rm -rf /opt/postgis \
## UTF8Proc
 && cd /opt/ \
 && git clone https://github.com/JuliaLang/utf8proc.git \
 && cd utf8proc \
 && git checkout -q v2.0.2 \
 && make \
 && make install \
 && ldconfig \
 && rm -rf /opt/utf8proc \
## Mapnik German
 && cd /opt/ \
 && git clone https://github.com/openmaptiles/mapnik-german-l10n.git \
 && cd mapnik-german-l10n \
 && make \
 && make install \
 && rm -rf /opt/mapnik-german-l10n \
## Cleanup
 && apt-get -qq -y --auto-remove purge \
        autoconf \
        automake \
        autotools-dev \
        build-essential \
        ca-certificates \
        bison \
        cmake \
        curl \
        dblatex \
        docbook-mathml \
        docbook-xsl \
        git \
        libcunit1-dev \
        libtool \
        make \
        g++ \
        gcc \
        pandoc \
        unzip \
        xsltproc \
&& rm -rf /var/lib/apt/lists/*

COPY ./initdb-postgis.sh /docker-entrypoint-initdb.d/10_postgis.sh
