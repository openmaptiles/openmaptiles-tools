# There is an issue updating to postgis 12:
# the postgis base image has outdated ogr2ogr (gdal-bin package)
# does not support PG12 yet, which means postgis-preloaded cannot be built easily.
# Once it is updated, or there is a different way to build it, we can upgrade to 12.
FROM postgis/postgis:11-2.5

LABEL MAINTAINER="Yuri Astrakhan <YuriAstrakhan@gmail.com>"

ENV UTF8PROC_TAG=v2.2.0 \
    MAPNIK_GERMAN_L10N_TAG=v2.5.5 \
    PGSQL_GZIP_HASH=33b640b72836f5ad05840a0ee55be5e34839eb39

RUN apt-get -qq -y update \
    ##
    ## Install build dependencies
    && apt-get -qq -y --no-install-recommends install \
        build-essential \
        ca-certificates \
        # Required by Nominatim to download data files
        curl \
        git \
        pandoc \
        # $PG_MAJOR is declared in postgres docker
        postgresql-server-dev-$PG_MAJOR \
        libkakasi2-dev \
        libgdal-dev \
    ##
    ## gzip extension
    && cd /opt/ \
    && git clone https://github.com/pramsey/pgsql-gzip.git \
    && cd pgsql-gzip \
    && git checkout -q $PGSQL_GZIP_HASH \
    && make \
    && make install \
    && rm -rf /opt/pgsql-gzip \
    ##
    ## UTF8Proc
    && cd /opt/ \
    && git clone https://github.com/JuliaLang/utf8proc.git \
    && cd utf8proc \
    && git checkout -q $UTF8PROC_TAG \
    && make \
    && make install \
    && ldconfig \
    && rm -rf /opt/utf8proc \
    ##
    ## osml10n extension (originally Mapnik German)
    && cd /opt/ \
    && git clone https://github.com/giggls/mapnik-german-l10n.git \
    && cd mapnik-german-l10n \
    && git checkout -q $MAPNIK_GERMAN_L10N_TAG \
    && make \
    && make install \
    && rm -rf /opt/mapnik-german-l10n \
    ##
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
        libpq-dev \
        postgresql-server-dev-$PG_MAJOR \
        libxml2-dev \
        libjson-c-dev \
        libgdal-dev \
    && rm -rf /usr/local/lib/*.a \
    && rm -rf /var/lib/apt/lists/*

# The script should run after the parent's postgis.sh runs
# so it must have the name that's listed after "postgis.sh"
COPY ./initdb-postgis.sh /docker-entrypoint-initdb.d/postgisZ.sh
