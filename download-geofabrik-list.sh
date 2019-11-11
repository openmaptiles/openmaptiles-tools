#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

download-geofabrik generate
download-geofabrik list

