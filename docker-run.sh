#!/bin/bash
set -e

: "${DOCKER_IMAGE:=openmaptiles/openmaptiles-tools}"

# Current dir is shared with the docker, allowing it to write to it as a current user
WORKDIR="$( pwd -P )"

docker run --rm \
        -u $(id -u ${USER}):$(id -g ${USER}) \
        -v "${WORKDIR}:/tileset" \
        "${DOCKER_IMAGE}" "$@"
