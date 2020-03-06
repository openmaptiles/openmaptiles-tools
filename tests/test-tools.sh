#!/usr/bin/env bash

set -o errexit  # -e
set -o pipefail
set -o nounset  # -u

TESTS=tests
TESTLAYERS="$TESTS/testlayers"
HTTPDIR="$TESTS/http"
DEVDOC=${BUILD?}/devdoc
mkdir -p "${DEVDOC}"

set -x

generate-tm2source "$TESTLAYERS/testmaptiles.yaml" \
      --host="pghost" --port=5432 --database="pgdb" --user="pguser" --password="pgpswd" > "$BUILD/tm2source.yml"

generate-imposm3  "$TESTLAYERS/testmaptiles.yaml"                                 > "$BUILD/imposm3.yaml"

generate-sql      "$TESTLAYERS/testmaptiles.yaml"                                 > "$BUILD/sql.sql"
generate-sql      "$TESTLAYERS/testmaptiles.yaml" --dir "$BUILD/parallel_sql"

generate-sqltomvt "$TESTLAYERS/testmaptiles.yaml"                                 > "$BUILD/mvttile_func.sql"
generate-sqltomvt "$TESTLAYERS/testmaptiles.yaml" --key                           > "$BUILD/mvttile_func_key.sql"
generate-sqltomvt "$TESTLAYERS/testmaptiles.yaml" --psql                          > "$BUILD/mvttile_psql.sql"
generate-sqltomvt "$TESTLAYERS/testmaptiles.yaml" --prepared                      > "$BUILD/mvttile_prep.sql"
generate-sqltomvt "$TESTLAYERS/testmaptiles.yaml" --query                         > "$BUILD/mvttile_query.sql"
generate-sqltomvt "$TESTLAYERS/testmaptiles.yaml" --query --gzip                  > "$BUILD/mvttile_query_gzip.sql"
generate-sqltomvt "$TESTLAYERS/testmaptiles.yaml" --query --gzip 9                > "$BUILD/mvttile_query_gzip9.sql"
generate-sqltomvt "$TESTLAYERS/testmaptiles.yaml" --query --no-feature-ids        > "$BUILD/mvttile_query_no_feat_ids.sql"
generate-sqltomvt "$TESTLAYERS/testmaptiles.yaml" --query --postgis-ver 2.4.0dev  > "$BUILD/mvttile_query_v2.4.0dev.sql"
generate-sqltomvt "$TESTLAYERS/testmaptiles.yaml" --query \
                      --postgis-ver 'ABC="" POSTGIS="2.4.0dev r15415" PGSQL="96"' > "$BUILD/mvttile_query_v2.4.0dev-a.sql"
generate-sqltomvt "$TESTLAYERS/testmaptiles.yaml" --query --postgis-ver 2.4.8     > "$BUILD/mvttile_query_v2.4.8.sql"
generate-sqltomvt "$TESTLAYERS/testmaptiles.yaml" --query \
                      --postgis-ver 'ABC="" POSTGIS="2.4.8 r17696" PGSQL="96"'    > "$BUILD/mvttile_query_v2.4.8-a.sql"
generate-sqltomvt "$TESTLAYERS/testmaptiles.yaml" --query --postgis-ver 2.5       > "$BUILD/mvttile_query_v2.5.sql"
generate-sqltomvt "$TESTLAYERS/testmaptiles.yaml" --query --postgis-ver 3.0       > "$BUILD/mvttile_query_v3.0.sql"
generate-sqltomvt "$TESTLAYERS/testmaptiles.yaml" --query --test-geometry         > "$BUILD/mvttile_query_test_geom.sql"
generate-sqltomvt "$TESTLAYERS/testmaptiles.yaml" --query --test-geometry --key   > "$BUILD/mvttile_query_test_geom_key.sql"
generate-doc      "$TESTLAYERS/housenumber/housenumber.yaml"                      > "$BUILD/doc.md"
generate-sqlquery "$TESTLAYERS/housenumber/housenumber.yaml" 14                   > "$BUILD/sqlquery.sql"

generate-etlgraph "$TESTLAYERS/testmaptiles.yaml" "$DEVDOC" --keep -f png -f svg
generate-etlgraph "$TESTLAYERS/housenumber/housenumber.yaml" "$DEVDOC" --keep -f png -f svg

generate-mapping-graph "$TESTLAYERS/testmaptiles.yaml" "$DEVDOC" --keep -f png -f svg
generate-mapping-graph "$TESTLAYERS/housenumber/housenumber.yaml" "$DEVDOC/mapping_diagram" --keep -f png -f svg

download-osm planet --dry-run
download-osm geofabrik michigan --dry-run


# Run background http server, and stop it when this script exits
python -m http.server 8555 -d "$HTTPDIR" &
# the $! should be expanded right away, not when the trap occurs, so on exit it stops http service
# shellcheck disable=SC2064
trap "kill $!" EXIT

download-osm url http://localhost:8555/monaco-20150428.osm.pbf \
  --verbose --make-dc "$BUILD/monaco-dc.yml" --id raw-url --minzoom 0 --maxzoom 10 -- --dir /tmp

# Test downloader support for env vars
export OSM_AREA_NAME=monaco-test2
export MIN_ZOOM=3
export MAX_ZOOM=5
download-osm url http://localhost:8555/monaco-20150428.osm.pbf \
  --verbose --make-dc "$BUILD/monaco-dc2.yml" -- --dir /tmp
unset OSM_AREA_NAME MIN_ZOOM MAX_ZOOM

# Using a fake cache/geofabrik.json so that downloader wouldn't need to download the real one from Geofabrik site
download-osm geofabrik monaco-test \
  --verbose --make-dc "$BUILD/monaco-dc3.yml" --minzoom 5 --maxzoom 6 -- --dir /tmp
