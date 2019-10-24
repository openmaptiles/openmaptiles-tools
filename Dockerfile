FROM python:3.7

WORKDIR /usr/src/app

# Using VT_UTIL_DIR and OMT_UTIL_DIR vars allow users to provide custom util files:
# postgis-vt-util.sql and language.sql
# See README
ENV PATH="/usr/src/app:${PATH}" \
    VT_UTIL_DIR=/opt/postgis-vt-util \
    VT_UTIL_URL="https://raw.githubusercontent.com/mapbox/postgis-vt-util/v1.0.0/postgis-vt-util.sql" \
    VT_TILEBBOX_URL="https://raw.githubusercontent.com/mapbox/postgis-vt-util/master/src/TileBBox.sql" \
    OMT_UTIL_DIR=/usr/src/app/sql \
    SQL_DIR=/sql

RUN apt-get update \
    && apt-get install  -y --no-install-recommends \
        graphviz \
        sqlite3 \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/

# Copy requirements.txt first to avoid pip install on every code change
COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN curl -OL $VT_UTIL_URL && \
    curl -OL $VT_TILEBBOX_URL && \
    mkdir -p "$VT_UTIL_DIR" && \
    mv postgis-vt-util.sql TileBBox.sql ${VT_UTIL_DIR}/ && \
    mv bin/* . && \
    rm -rf bin && \
    rm requirements.txt

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
