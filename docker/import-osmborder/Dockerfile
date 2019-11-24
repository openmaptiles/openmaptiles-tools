ARG BASE_TAG=latest
FROM openmaptiles/openmaptiles-tools:${BASE_TAG}
LABEL maintainer="YuriAstrakhan@gmail.com"

ARG RELEASE_VERSION="v3.0.0-beta"
# In case there is no osmborder_lines published on github under RELEASE_VERSION version, use this one
ARG FALLBACK_DUMP_VERSION="v3.0.0-beta"

ENV PGFUTTER_VERSION="v1.2" \
    RELEASES_PREFIX="https://github.com/openmaptiles/openmaptiles-tools/releases/download/" \
    OSM_BORDERS_FILE="osmborder_lines.csv.gz" \
    WGET="wget --quiet --progress=bar:force:noscroll --show-progress" \
    IMPORT_DIR=/import

RUN $WGET -O /usr/local/bin/pgfutter \
         "https://github.com/lukasmartinelli/pgfutter/releases/download/${PGFUTTER_VERSION}/pgfutter_linux_amd64" \
 && chmod +x /usr/local/bin/pgfutter \
 && mkdir -p "${IMPORT_DIR}" \
 && cd "${IMPORT_DIR}" \
 # Try to download from the current release version
 && if $WGET -O "${OSM_BORDERS_FILE}" "${RELEASES_PREFIX}/${RELEASE_VERSION}/${OSM_BORDERS_FILE}"; then \
        echo "Used borders file from ${RELEASE_VERSION} release"; \
    elif $WGET -O "${OSM_BORDERS_FILE}" "${RELEASES_PREFIX}/${FALLBACK_DUMP_VERSION}/${OSM_BORDERS_FILE}"; then \
        echo "Release ${RELEASE_VERSION} not found, used file from the fallback ${FALLBACK_DUMP_VERSION} release"; \
    fi \
 && gzip -d "${OSM_BORDERS_FILE}"

WORKDIR /usr/src/app/
COPY . /usr/src/app/
CMD ["./import_osmborder_lines.sh"]
