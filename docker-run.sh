#!/bin/bash
set -e

: ${VERSION:=$(cat VERSION)}
: ${IMAGE_NAME:=openmaptiles/openmaptiles-tools}
: ${DOCKER_IMAGE:=${IMAGE_NAME}:${VERSION}}
: ${DOCKER_USER:=$(id -u ${USER}):$(id -g ${USER})}

# Current dir is shared with the docker, allowing scripts to write to the dir as a current user
: ${WORKDIR:="$( pwd -P )"}

if [[ -t 1 ]]; then
  # Running in a terminal
  : ${DOCKER_OPTS:="-it --rm"}
else
  : ${DOCKER_OPTS:="--rm"}
fi

set -x
docker run ${DOCKER_OPTS} -u "${DOCKER_USER}" -v "${WORKDIR}:/tileset" "${DOCKER_IMAGE}" "$@"
