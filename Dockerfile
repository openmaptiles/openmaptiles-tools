FROM python:3.8

WORKDIR /usr/src/app

# Using VT_UTIL_DIR and OMT_UTIL_DIR vars allow users to provide custom util files:
# postgis-vt-util.sql and language.sql
# See README
ENV VT_UTIL_DIR=/opt/postgis-vt-util \
    OMT_UTIL_DIR=/usr/src/app/sql \
    SQL_DIR=/sql \
    OSMBORDER_REV=e3ae8f7a2dcdcd6dc80abab4679cb5edb7dc6fa5 \
    PGFUTTER_VERSION="v1.2" \
    WGET="wget --quiet --progress=bar:force:noscroll --show-progress" \
    GOPATH=/go \
    PATH="/usr/src/app:/usr/local/go/bin:/go/bin:${PATH}"

ARG PG_MAJOR=12
ARG IMPOSM_REPO="https://github.com/omniscale/imposm3.git"
ARG IMPOSM_VERSION="v0.10.0"


RUN set -eux ;\
    /bin/bash -c 'echo ""; echo ""; echo "##### Installing packages..."' >&2 ;\
    curl https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - ;\
    /bin/bash -c 'source /etc/os-release && echo "deb http://apt.postgresql.org/pub/repos/apt/ ${VERSION_CODENAME?}-pgdg main ${PG_MAJOR?}" > /etc/apt/sources.list.d/pgdg.list' ;\
    DEBIAN_FRONTEND=noninteractive apt-get update ;\
    DEBIAN_FRONTEND=noninteractive apt-get install  -y --no-install-recommends \
        aria2     `# multi-stream file downloader` \
        graphviz  `# used by layer mapping graphs` \
        sqlite3   `# mbtiles file manipulations`   \
        gdal-bin  `# installs ogr2ogr` \
        osmctools `# osmconvert and other OSM tools` \
        postgresql-client-${PG_MAJOR?} \
        \
        `# tools to build osmborder` \
        build-essential \
        ca-certificates \
        cmake \
        git \
        libosmium2-dev \
        wget \
        zlib1g-dev \
        ;\
    \
    \
    :
RUN set -eux ;\
    /bin/bash -c 'echo ""; echo ""; echo "##### Building osmborder -- https://github.com/pnorman/osmborder"' >&2 ;\
    git clone https://github.com/pnorman/osmborder.git /usr/src/osmborder ;\
    cd /usr/src/osmborder ;\
    git checkout ${OSMBORDER_REV?} ;\
    mkdir -p /usr/src/osmborder/build ;\
    cd /usr/src/osmborder/build ;\
    cmake .. ;\
    make ;\
    make install ;\
    rm -rf /usr/src/osmborder ;\
    \
    \
    :
RUN set -eux ;\
    /bin/bash -c 'echo ""; echo ""; echo "##### Installing pgfutter -- https://github.com/lukasmartinelli/pgfutter"' >&2 ;\
    $WGET -O /usr/local/bin/pgfutter \
       "https://github.com/lukasmartinelli/pgfutter/releases/download/${PGFUTTER_VERSION}/pgfutter_linux_amd64" ;\
    chmod +x /usr/local/bin/pgfutter ;\
    \
    \
    :
RUN set -eux ;\
    /bin/bash -c 'echo ""; echo ""; echo "##### Installing go-lang"' >&2 ;\
    $WGET -O /tmp/go.tgz "https://dl.google.com/go/go1.13.8.linux-amd64.tar.gz" ;\
    tar -C /usr/local -xzf /tmp/go.tgz ;\
    rm /tmp/go.tgz ;\
    go version ;\
    mkdir -p "$GOPATH/src" "$GOPATH/bin" ;\
    chmod -R 777 "$GOPATH" ;\
    \
    \
    :
RUN set -eux ;\
    /bin/bash -c 'echo ""; echo ""; echo "##### Install imposm3 -- https://github.com/osm2vectortiles/imposm3"' >&2 ;\
    mkdir -p $GOPATH/src/github.com/omniscale/imposm3 ;\
    cd  $GOPATH/src/github.com/omniscale/imposm3 ;\
    go get github.com/tools/godep ;\
    #
    # get and build specific version of imposm
    :
RUN set -eux ;\
    git clone --quiet --depth 1 $IMPOSM_REPO -b $IMPOSM_VERSION \
        $GOPATH/src/github.com/omniscale/imposm3 ;\
    :
RUN set -eux ;\
    cd $GOPATH/src/github.com/omniscale/imposm3 ;\
    make build ;\
    :
RUN set -eux ;\
    #
    # Support legacy imposm3 as well as the newer imposm app name
    ( [ -f imposm ] && mv imposm /usr/bin/imposm || mv imposm3 /usr/bin/imposm ) ;\
    ln -s /usr/bin/imposm /usr/bin/imposm3 ;\
    \
    \
    :
RUN set -eux ;\
    /bin/bash -c 'echo ""; echo ""; echo "##### Cleaning up"' >&2 ;\
    rm -rf /var/lib/apt/lists/*  ;\
    rm -rf $GOPATH/bin/godep ;\
    rm -rf $GOPATH/src/ ;\
    rm -rf $GOPATH/pkg/


# Copy requirements.txt first to avoid pip install on every code change
COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN set -eux ;\
    curl -OL https://raw.githubusercontent.com/openmaptiles/postgis-vt-util/v2.0.0/postgis-vt-util.sql ;\
    mkdir -p "${VT_UTIL_DIR?}" ;\
    mv postgis-vt-util.sql "${VT_UTIL_DIR?}/" ;\
    mv bin/* . ;\
    rm -rf bin ;\
    rm requirements.txt ;\
    ./download-osm list geofabrik

WORKDIR /tileset
VOLUME /tileset
VOLUME /sql

# In case there are no parameters, print a list of available scripts
CMD echo "*******************************************************************" && \
    echo "  Please specify a script to run. Here are the available scripts." && \
    echo "  Use script name with --help to get more information." && \
    echo "  Use 'bash' to start a shell inside the tools container." && \
    echo "*******************************************************************" && \
    find /usr/src/app -maxdepth 1 -executable -type f -printf " * %f\n" | sort
