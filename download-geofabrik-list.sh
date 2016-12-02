#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

download-geofabrik update
download-geofabrik list

