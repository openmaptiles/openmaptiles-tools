FROM golang:1.13 as go-builder

# By default for now use custom build until we verify everything is stable
ARG IMPOSM_REPO="https://github.com/openmaptiles/imposm3.git"
ARG IMPOSM_VERSION="v2017-10-18"

# Current version, disable for now
#ARG IMPOSM_REPO="https://github.com/omniscale/imposm3.git"
#ARG IMPOSM_VERSION="v0.10.0"

# Build imposm
RUN set -eux ;\
    DEBIAN_FRONTEND=noninteractive apt-get update ;\
    DEBIAN_FRONTEND=noninteractive apt-get install  -y \
        `# installing imposm dependencies` \
        libgeos-dev \
        libleveldb-dev \
        libprotobuf-dev \
        ;\
    \
    apt list --installed ;\
    \
    go version ;\
    go get github.com/tools/godep ;\
    mkdir /build-bin ;\
    \
    /bin/bash -c 'echo ""; echo ""; echo "##### Build imposm3 -- https://github.com/osm2vectortiles/imposm3"' >&2 ;\
    #
    # get and build specific version of imposm
    git clone --quiet --depth 1 $IMPOSM_REPO -b $IMPOSM_VERSION \
        $GOPATH/src/github.com/omniscale/imposm3 ;\
    cd $GOPATH/src/github.com/omniscale/imposm3 ;\
    make build ;\
    # Older imposm executable was called imposm3 - rename it to the common name "imposm"
    ( [ -f imposm ] && mv imposm /build-bin/imposm || mv imposm3 /build-bin/imposm )


# Build osmborder
FROM python:3.8 as c-builder
ARG OSMBORDER_REV=e3ae8f7a2dcdcd6dc80abab4679cb5edb7dc6fa5

RUN set -eux ;\
    mkdir /build-bin ;\
    DEBIAN_FRONTEND=noninteractive apt-get update ;\
    DEBIAN_FRONTEND=noninteractive apt-get install  -y --no-install-recommends \
        `# installing osmborder dependencies` \
        build-essential \
        ca-certificates \
        cmake \
        git \
        libosmium2-dev \
        zlib1g-dev \
        ;\
    /bin/bash -c 'echo ""; echo ""; echo "##### Building osmborder -- https://github.com/pnorman/osmborder"' >&2 ;\
    git clone https://github.com/pnorman/osmborder.git /usr/src/osmborder ;\
    cd /usr/src/osmborder ;\
    git checkout ${OSMBORDER_REV:?} ;\
    mkdir -p /usr/src/osmborder/build ;\
    cd /usr/src/osmborder/build ;\
    cmake .. ;\
    make ;\
    make install ;\
    mv /usr/src/osmborder/build/src/osmborder /build-bin ;\
    mv /usr/src/osmborder/build/src/osmborder_filter /build-bin


# Primary image
FROM python:3.8-slim
LABEL maintainer="Yuri Astrakhan <YuriAstrakhan@gmail.com>"

ARG PG_MAJOR=12
ARG VT_UTIL_VERSION=v2.0.0
ARG TOOLS_DIR=/usr/src/app

WORKDIR ${TOOLS_DIR}

#
# IMPOSM_CONFIG_FILE can be used to provide custom IMPOSM config file
# SQL_TOOLS_DIR can be used to provide custom SQL files instead of vt_utils and other files from /sql
#
ENV TOOLS_DIR="$TOOLS_DIR" \
    PATH="${TOOLS_DIR}:${PATH}" \
    IMPOSM_CONFIG_FILE=${TOOLS_DIR}/config/repl_config.json \
    IMPOSM_MAPPING_FILE=/mapping/mapping.yaml \
    IMPOSM_CACHE_DIR=/cache \
    IMPOSM_DIFF_DIR=/import \
    PBF_DATA_DIR=/import \
    SQL_DIR=/sql \
    SQL_TOOLS_DIR="${TOOLS_DIR}/sql"


RUN set -eux ;\
    /bin/bash -c 'echo ""; echo ""; echo "##### Installing packages..."' >&2 ;\
    DEBIAN_FRONTEND=noninteractive apt-get update ;\
    DEBIAN_FRONTEND=noninteractive apt-get install  -y --no-install-recommends \
        # a few common tools
        ca-certificates \
        curl \
        wget \
        git  \
        gnupg2  `# TODO: not sure why gnupg2 is needed`  ;\
    curl https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - ;\
    /bin/bash -c 'source /etc/os-release && echo "deb http://apt.postgresql.org/pub/repos/apt/ ${VERSION_CODENAME:?}-pgdg main ${PG_MAJOR:?}" > /etc/apt/sources.list.d/pgdg.list' ;\
    DEBIAN_FRONTEND=noninteractive apt-get update ;\
    DEBIAN_FRONTEND=noninteractive apt-get install  -y --no-install-recommends \
        aria2     `# multi-stream file downloader` \
        graphviz  `# used by layer mapping graphs` \
        sqlite3   `# mbtiles file manipulations`   \
        gdal-bin  `# contains ogr2ogr` \
        osmctools `# osmconvert and other OSM tools` \
        osmosis   `# useful toolset - https://wiki.openstreetmap.org/wiki/Osmosis` \
        postgresql-client-${PG_MAJOR:?}  `# psql` \
        \
        `# imposm dependencies` \
        libgeos-dev \
        libleveldb-dev \
        libprotobuf-dev \
        ;\
    \
    /bin/bash -c 'echo ""; echo ""; echo "##### Cleaning up"' >&2 ;\
    rm -rf /var/lib/apt/lists/*

# Copy requirements.txt first to avoid pip install on every code change
COPY ./requirements.txt .

RUN set -eux ;\
    pip install --no-cache-dir -r requirements.txt ;\
    mkdir -p "${SQL_TOOLS_DIR:?}" ;\
    wget --quiet --progress=bar:force:noscroll --show-progress -O "${SQL_TOOLS_DIR}/10_postgis-vt-util.sql" \
       https://raw.githubusercontent.com/openmaptiles/postgis-vt-util/${VT_UTIL_VERSION}/postgis-vt-util.sql

# Copy tools, imposm, and osmborder into the app dir
COPY --from=go-builder /build-bin/* ./
COPY --from=c-builder /build-bin/* ./
COPY . .

RUN set -eux ;\
    mv bin/* . ;\
    rm -rf bin ;\
    rm requirements.txt ;\
    ./download-osm list geofabrik

WORKDIR /tileset

# In case there are no parameters, print a list of available scripts
CMD echo "*******************************************************************" ;\
    echo "  Please specify a script to run. Here are the available scripts." ;\
    echo "  Use script name with --help to get more information." ;\
    echo "  Use 'bash' to start a shell inside the tools container." ;\
    echo "*******************************************************************" ;\
    find "${TOOLS_DIR}" -maxdepth 1 -executable -type f -printf " * %f\n" | sort
