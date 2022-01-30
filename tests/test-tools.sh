#!/usr/bin/env bash

set -o errexit  # -e
set -o pipefail
set -o nounset  # -u

TESTS=tests
TESTLAYERS="$TESTS/testlayers"
HTTPDIR="$TESTS/http"
TEMP_DIR="/tmp"
DEVDOC=${BUILD:?}/devdoc
mkdir -p "$DEVDOC"

set -x

generate-tm2source "$TESTLAYERS/testmaptiles.yaml" \
      --host="pghost" --port=5432 --database="pgdb" --user="pguser" --password="pgpswd" > "$BUILD/tm2source.yml"
generate-tm2source "$TESTLAYERS/testmaptiles.yaml" \
      --pghost="pghost" --pgport=5432 --dbname="pgdb" --user="pguser" --password="pgpswd" > "$BUILD/tm2source2.yml"
generate-tm2source "$TESTLAYERS/testmaptiles.yaml" > "$BUILD/tm2source3.yml"

generate-imposm3  "$TESTLAYERS/testmaptiles.yaml"                                 > "$BUILD/imposm3.yaml"

generate-sql      "$TESTLAYERS/testmaptiles.yaml"                                 > "$BUILD/sql.sql"
generate-sql      "$TESTLAYERS/testmaptiles.yaml" --dir "$BUILD/parallel_sql"
generate-sql      "$TESTLAYERS/testmaptiles.yaml" --dir "$BUILD/parallel_sql2" --nodata

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

echo "++++++++++++++++++++++++"
echo "Testing download-osm"
echo "++++++++++++++++++++++++"

# Using a fake cache/geofabrik.json so that downloader wouldn't need to download the real one from Geofabrik site
download-osm planet --imposm-cfg "$BUILD/planet-cfg.json" --dry-run
download-osm michigan --imposm-cfg "$BUILD/michigan-cfg.json" --dry-run


# Run background http server, and stop it when this script exits
python -m http.server 8555 -d "$HTTPDIR" &
# the $! should be expanded right away, not when the trap occurs, so on exit it stops http service
# shellcheck disable=SC2064
trap "kill $!" EXIT

download-osm url http://localhost:8555/monaco-20150428.osm.pbf \
  --output "$TEMP_DIR/monaco-20150428.osm.pbf" --verbose --bbox "$BUILD/monaco.bbox"

download-osm bbox "$TEMP_DIR/monaco-20150428.osm.pbf" "$BUILD/monaco.bbox" --verbose
diff --brief "$HTTPDIR/monaco-20150428.osm.pbf" "$TEMP_DIR/monaco-20150428.osm.pbf"
rm "$TEMP_DIR/monaco-20150428.osm.pbf"

download-osm geofabrik monaco-test \
  --verbose --imposm-cfg "$BUILD/monaco-cfg.json" --kv foo=bar --kv replication_interval=4h \
  --bbox "$BUILD/monaco2.bbox" --output "$TEMP_DIR/monaco-20150428.osm.pbf"
diff --brief "$HTTPDIR/monaco-20150428.osm.pbf" "$TEMP_DIR/monaco-20150428.osm.pbf"
rm "$TEMP_DIR/monaco-20150428.osm.pbf"


echo "++++++++++++++++++++++++"
echo "Testing debug-mvt"
echo "++++++++++++++++++++++++"

debug-mvt dump "$HTTPDIR/osm_13_4388_2568.mvt" > "$BUILD/debug_mvt_dump.out"
debug-mvt dump "$HTTPDIR/osm_13_4388_2568.mvt" --summary > "$BUILD/debug_mvt_dump_summary.out"
debug-mvt dump "$HTTPDIR/osm_13_4388_2568.mvt" --show-names > "$BUILD/debug_mvt_dump_show_names.out"
debug-mvt dump "$HTTPDIR/osm_13_4388_2568.mvt" --show-names --sort-output > "$BUILD/debug_mvt_dump_show_names_sorted.out"
debug-mvt dump "$HTTPDIR/osm_13_4388_2568.mvt" --summary --show-names > "$BUILD/debug_mvt_dump_summary_show_names.out"
debug-mvt dump "http://localhost:8555/osm_13_4388_2568.mvt" --summary > "$BUILD/debug_mvt_URL_dump_summary.out"
gzip < "$HTTPDIR/osm_13_4388_2568.mvt" | debug-mvt dump - --summary > "$BUILD/debug_mvt_STDIN_dump_summary.out"

{ set +x ;} 2> /dev/null
echo "-----------------------------------------------------------"
echo "-------- Finished $0 --------"
echo "-----------------------------------------------------------"
