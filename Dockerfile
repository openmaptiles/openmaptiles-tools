FROM python:3.8

WORKDIR /usr/src/app

# Using VT_UTIL_DIR and OMT_UTIL_DIR vars allow users to provide custom util files:
# postgis-vt-util.sql and language.sql
# See README
ENV PATH="/usr/src/app:${PATH}" \
    VT_UTIL_DIR=/opt/postgis-vt-util \
    OMT_UTIL_DIR=/usr/src/app/sql \
    SQL_DIR=/sql \
    OSMBORDER_REV=e3ae8f7a2dcdcd6dc80abab4679cb5edb7dc6fa5 \
    PGFUTTER_VERSION="v1.2" \
    WGET="wget --quiet --progress=bar:force:noscroll --show-progress"

ARG PG_MAJOR=12

RUN curl https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - \
    && /bin/bash -c 'source /etc/os-release && echo "deb http://apt.postgresql.org/pub/repos/apt/ ${VERSION_CODENAME?}-pgdg main ${PG_MAJOR?}" > /etc/apt/sources.list.d/pgdg.list' \
    && DEBIAN_FRONTEND=noninteractive apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install  -y --no-install-recommends \
        aria2     `# multi-stream file downloader` \
        graphviz  `# used by layer mapping graphs` \
        sqlite3   `# mbtiles file manipulations`   \
        gdal-bin  `# installs ogr2ogr` \
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
        \
    && rm -rf /var/lib/apt/lists/ \
    && (  `# Build osmborder` \
        git clone https://github.com/pnorman/osmborder.git /usr/src/osmborder \
        && cd /usr/src/osmborder \
        && git checkout ${OSMBORDER_REV?} \
        && mkdir -p /usr/src/osmborder/build \
        && cd /usr/src/osmborder/build \
        && cmake .. \
        && make \
        && make install \
        && rm -rf /usr/src/osmborder \
       ) \
    && (  `# Set up pgfutter` \
        $WGET -O /usr/local/bin/pgfutter \
           "https://github.com/lukasmartinelli/pgfutter/releases/download/${PGFUTTER_VERSION}/pgfutter_linux_amd64" \
        && chmod +x /usr/local/bin/pgfutter \
       )

# Copy requirements.txt first to avoid pip install on every code change
COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN curl -OL https://raw.githubusercontent.com/openmaptiles/postgis-vt-util/v2.0.0/postgis-vt-util.sql && \
    mkdir -p "${VT_UTIL_DIR?}" && \
    mv postgis-vt-util.sql "${VT_UTIL_DIR?}/" && \
    mv bin/* . && \
    rm -rf bin && \
    rm requirements.txt && \
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
