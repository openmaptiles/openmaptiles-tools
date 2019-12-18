#!/usr/bin/env bash
set -e

# Get package version from the openmaptiles/__init__.py
: "${VERSION:=$(grep '__version__' "$(dirname "$0")/openmaptiles/__init__.py" | sed -E 's/^(.*"([^"]+)".*|.*)$/\2/')}"
: "${IMAGE_NAME:=openmaptiles/openmaptiles-tools}"
: "${DOCKER_IMAGE:=${IMAGE_NAME}:${VERSION}}"
: "${DOCKER_USER:=$(id -u "${USER}"):$(id -g "${USER}")}"

# Current dir is shared with the docker, allowing scripts to write to the dir as a current user
: "${WORKDIR:="$( pwd -P )"}"

if [[ -t 1 ]]; then
  # Running in a terminal
  : "${DOCKER_OPTS:="-it --rm"}"
else
  : "${DOCKER_OPTS:="--rm"}"
fi

set -x
docker run ${DOCKER_OPTS} -u "${DOCKER_USER}" -v "${WORKDIR}:/tileset" "${DOCKER_IMAGE}" "$@"
