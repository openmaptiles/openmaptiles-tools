FROM debian:buster

RUN DEBIAN_FRONTEND=noninteractive apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    build-essential \
    zlib1g-dev \
    cmake \
    libosmium2-dev \
    git \
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
