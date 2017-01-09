FROM python:3.6

RUN apt-get update \ 
    && apt-get install  -y --no-install-recommends \
        graphviz \
        sqlite3 \
    && rm -rf /var/lib/apt/lists/

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY . /usr/src/app
RUN pip install .

RUN make test

WORKDIR /tileset
VOLUME /tileset
