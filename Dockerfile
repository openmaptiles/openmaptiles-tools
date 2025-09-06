FROM golang:1.17 AS go-builder
ARG IMPOSM_REPO="https://github.com/omniscale/imposm3.git"
ARG IMPOSM_VERSION="v0.11.1"

# Build imposm
RUN set -eux ;\
    DEBIAN_FRONTEND=noninteractive apt-get update ;\
    DEBIAN_FRONTEND=noninteractive apt-get install  -y \
        `# installing imposm dependencies` \
        libgeos-dev \
        libleveldb-dev \
        libprotobuf-dev \
        protobuf-compiler \
        ;\
    \
    apt list --installed ;\
    \
    go version ;\
    go get github.com/tools/godep ;\
    mkdir /build-bin ;\
    \
    /bin/bash -c 'echo ""; echo ""; echo "##### Build imposm3 -- $IMPOSM_REPO in version $IMPOSM_VERSION"' >&2 ;\
    #
    # get and build specific version of imposm
    git clone --quiet --depth 1 $IMPOSM_REPO -b $IMPOSM_VERSION \
        $GOPATH/src/github.com/omniscale/imposm3 ;\
    cd $GOPATH/src/github.com/omniscale/imposm3 ;\
    make build ;\
    # Older imposm executable was called imposm3 - rename it to the common name "imposm"
    ( [ -f imposm ] && mv imposm /build-bin/imposm || mv imposm3 /build-bin/imposm )


# Build SPREET
FROM rust:1.76 AS rust-builder
ARG SPREET_REPO="https://github.com/flother/spreet"
ARG SPREET_VERSION="v0.11.0"

RUN set -eux ;\
    /bin/bash -c 'echo ""; echo ""; echo "##### Build Spreet -- $SPREET_REPO -- version $SPREET_VERSION"' >&2 ;\
    git clone --quiet --depth 1 $SPREET_REPO -b $SPREET_VERSION ;\
    cd spreet ;\
    cargo build --release ;\
    mkdir /build-bin ;\
    mv target/release/spreet /build-bin

# Primary image
FROM python:3.9-slim
LABEL maintainer="Yuri Astrakhan <YuriAstrakhan@gmail.com>"

ARG PG_MAJOR=14
ARG TOOLS_DIR=/usr/src/app

WORKDIR ${TOOLS_DIR}

#
# IMPOSM_CONFIG_FILE can be used to provide custom IMPOSM config file
# SQL_TOOLS_DIR can be used to provide custom SQL files instead of the files from /sql
#
ENV TOOLS_DIR="$TOOLS_DIR" \
    PATH="${TOOLS_DIR}/bin:${PATH}" \
    PYTHONPATH="${TOOLS_DIR}:${PYTHONPATH}" \
    IMPOSM_CONFIG_FILE=${TOOLS_DIR}/config/repl_config.json \
    IMPOSM_MAPPING_FILE=/mapping/mapping.yaml \
    IMPOSM_CACHE_DIR=/usr/src/app/cache \
    IMPOSM_DIFF_DIR=/import \
    EXPIRETILES_DIR=/import \
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
        less \
        nano \
        procps  `# ps command` \
        gnupg2  `# TODO: not sure why gnupg2 is needed`  ;\
    curl https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /usr/share/keyrings/postgresql-keyring.gpg ;\
    /bin/bash -c 'source /etc/os-release && echo "deb [signed-by=/usr/share/keyrings/postgresql-keyring.gpg] http://apt.postgresql.org/pub/repos/apt/ ${VERSION_CODENAME:?}-pgdg main ${PG_MAJOR:?}" > /etc/apt/sources.list.d/pgdg.list' ;\
    DEBIAN_FRONTEND=noninteractive apt-get update ;\
    DEBIAN_FRONTEND=noninteractive apt-get install  -y --no-install-recommends \
        aria2     `# multi-stream file downloader - used by download-osm` \
        graphviz  `# used by layer mapping graphs` \
        sqlite3   `# mbtiles file manipulations` \
        postgresql-client-${PG_MAJOR:?} \
        postgresql-${PG_MAJOR:?}-postgis-3 \
        osmium-tool \
        osmctools `# contains osmconvert` \
        ;\
    apt-get clean ;\
    rm -rf /var/lib/apt/lists/*

# Copy built binaries from build stages
COPY --from=go-builder /build-bin/imposm /usr/local/bin/
COPY --from=rust-builder /build-bin/spreet /usr/local/bin/

# Copy Python tools
COPY . ${TOOLS_DIR}/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p /cache /import /mapping

# Set proper permissions
RUN chmod +x ${TOOLS_DIR}/bin/*

# Default command
CMD ["/bin/bash"]