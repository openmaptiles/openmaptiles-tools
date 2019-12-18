# Use a separate docker for downloading to minimize final docker image
# BASE_TAG will be injected by the dockerhub auto-build environment
ARG BASE_TAG=latest
FROM openmaptiles/openmaptiles-tools:${BASE_TAG}

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY . /usr/src/app
RUN pip install . \
    && mv bin/* .

WORKDIR /import
VOLUME /import

CMD ["import-wikidata"]
