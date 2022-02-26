#!/usr/bin/env bash

set -o errexit  # -e
set -o pipefail
set -o nounset  # -u

# assumes the /omt is mapped to the root of the openmaptiles-tools repo

export PGHOST="${POSTGRES_HOST:-${PGHOST?}}"
export PGDATABASE="${POSTGRES_DB:-${PGDATABASE?}}"
export PGUSER="${POSTGRES_USER:-${PGUSER?}}"
export PGPASSWORD="${POSTGRES_PASSWORD:-${PGPASSWORD?}}"
export PGPORT="${POSTGRES_PORT:-${PGPORT:-5432}}"

set -x

MAX_RETRIES=40  # Maximum number of pg_isready calls
tries=0
while ! pg_isready
do
    tries=$((tries + 1))
    if (( tries > MAX_RETRIES )); then
        exit 1
    fi
    sleep 2
done

sleep 1

# Import all pre-required SQL code
source import-sql

echo "++++++++++++++++++++++++"
echo "Running OMT SQL tests"
echo "++++++++++++++++++++++++"

mkdir -p /omt/build

for sql_file in /omt/tests/sql/*.sql; do
  # Ensure output file can be deleted though it is owned by root
  out_file="/omt/build/$(basename "$sql_file").out"
  truncate --size 0 "$out_file"
  chmod 666 "$out_file"
  echo "Executing $sql_file and recording results in $out_file"
  psql -v ON_ERROR_STOP=1 --file "$sql_file" >> "$out_file"
done


echo "++++++++++++++++++++++++"
echo "Running import-borders tests"
echo "++++++++++++++++++++++++"

BORDERS_OUT=/omt/build/import-borders.csv

echo "++++++ Parsing PBF file into CSV..."
BORDERS_CSV_FILE=$BORDERS_OUT \
  /omt/bin/import-borders parse /omt/tests/http/monaco-20150428.osm.pbf
echo "++++++ Load parsed CSV file into a table"
/omt/bin/import-borders load "$BORDERS_OUT"
echo "++++++ Importing a PBF file into a DB table"
/omt/bin/import-borders import /omt/tests/http/monaco-20150428.osm.pbf
echo "++++++ Importing a PBF file into a DB table without import command"
/omt/bin/import-borders /omt/tests/http/monaco-20150428.osm.pbf
echo "++++++ Importing first found PBF file into a DB table by scanning a dir"
PBF_DATA_DIR=/omt/tests/http \
  BORDERS_PBF_FILE=/import/borders/filtered.pbf \
  BORDERS_CSV_FILE=/import/borders/lines.csv \
  /omt/bin/import-borders
echo "++++++ Importing a PBF file into a DB table with additional filtering"
BORDERS_CLEANUP=true \
  /omt/bin/import-borders import /omt/tests/http/monaco-20150428.osm.pbf

echo "++++++++++++++++++++++++"
echo "Testing mbtiles-tools"
echo "++++++++++++++++++++++++"
MBTILES_FILE="/tmp/data.mbtiles"
MBTILES2_FILE="/tmp/data2.mbtiles"
MBTILES3_FILE="/tmp/data3.mbtiles"
MBTILES4_FILE="/tmp/data4.mbtiles"
cp "/omt/tests/http/empty.mbtiles" "$MBTILES_FILE"
cp "/omt/tests/http/empty.mbtiles" "$MBTILES2_FILE"
cp /omt/tests/http/osm_13_4388_2568.mvt /tmp/osm_13_4388_2568.mvt
gzip /tmp/osm_13_4388_2568.mvt

sqlite3 "$MBTILES_FILE" <<'EOT'
INSERT INTO images (tile_id, tile_data) VALUES
  ('51d80b7172178334e9bde559411f0c84', readfile('/tmp/osm_13_4388_2568.mvt.gz')),
  ('7eccb2bcaa369aec6032de45548c15bc', 'openmaptiles'),
  ('0added1faded2cafe3facade45678901', 'pretend-dup');
INSERT INTO map (zoom_level, tile_column, tile_row, tile_id) VALUES
  (0, 0, 0, '7eccb2bcaa369aec6032de45548c15bc'),
  (1, 1, 1, '0added1faded2cafe3facade45678901'),
  (1, 1, 0, '51d80b7172178334e9bde559411f0c84'),
  (1, 0, 1, '0added1faded2cafe3facade45678901'),
  (1, 0, 0, '0added1faded2cafe3facade45678901');
EOT

sqlite3 "$MBTILES2_FILE" <<'EOT'
INSERT INTO images (tile_id, tile_data) VALUES
  ('51d80b7172178334e9bde559411f0c84', readfile('/tmp/osm_13_4388_2568.mvt.gz'));
INSERT INTO map (zoom_level, tile_column, tile_row, tile_id) VALUES
  (0, 0, 0, '7eccb2bcaa369aec6032de45548c15bc');
EOT

{
  echo "----------------------- mbtiles-tools meta-all --show-json --show-ranges"
  mbtiles-tools meta-all "$MBTILES_FILE" --show-json --show-ranges
  echo "----------------------- mbtiles-tools meta-set abc xyz"
  mbtiles-tools meta-set "$MBTILES_FILE" abc xyz
  mbtiles-tools meta-all "$MBTILES_FILE"
  echo "----------------------- mbtiles-tools meta-get abc"
  mbtiles-tools meta-get "$MBTILES_FILE" abc
  echo "----------------------- meta-generate meta-generate"
  mbtiles-tools meta-generate "$MBTILES_FILE" /omt/tests/testlayers/testmaptiles.yaml
  mbtiles-tools meta-all "$MBTILES_FILE" --show-json --show-ranges
  echo "----------------------- mbtiles-tools meta-set abc (delete)"
  mbtiles-tools meta-set "$MBTILES_FILE" abc
  mbtiles-tools meta-all "$MBTILES_FILE"
  echo "----------------------- meta-generate meta-generate --reset with overrides"
  export METADATA_ATTRIBUTION="set attr"
  export METADATA_DESCRIPTION="set desc"
  export METADATA_NAME="set name"
  export METADATA_VERSION="set ver"
  export BBOX="12.2403,35.8223,23.3262,45.8046"
  export CENTER_ZOOM=6
  mbtiles-tools meta-generate "$MBTILES_FILE" /omt/tests/testlayers/testmaptiles.yaml --reset --auto-minmax --show-ranges
  unset METADATA_ATTRIBUTION METADATA_DESCRIPTION METADATA_NAME METADATA_VERSION MIN_ZOOM MAX_ZOOM BBOX CENTER_ZOOM
  mbtiles-tools meta-all "$MBTILES_FILE" --show-json --show-ranges
  echo "----------------------- mbtiles-tools meta-copy"
  mbtiles-tools meta-set "$MBTILES2_FILE" foo bar
  mbtiles-tools meta-copy "$MBTILES_FILE" "$MBTILES2_FILE" --reset
  # Ignore filesize result because it could differ without vacuuming sqlite files first
  mbtiles-tools meta-all "$MBTILES_FILE" | grep -v '^filesize ' > /tmp/metaout1.out
  mbtiles-tools meta-all "$MBTILES2_FILE" | grep -v '^filesize ' > /tmp/metaout2.out
  diff --brief /tmp/metaout1.out /tmp/metaout2.out
  echo "----------------------- mbtiles-tools meta-copy with overrides"
  export METADATA_ATTRIBUTION="attr override"
  export METADATA_DESCRIPTION="desc override"
  export METADATA_NAME="name override"
  export METADATA_VERSION="ver override"
  export MIN_ZOOM=3
  export MAX_ZOOM=4
  export BBOX="15,40,27,48"
  export CENTER_ZOOM=8
  mbtiles-tools meta-copy "$MBTILES_FILE" "$MBTILES2_FILE" --reset
  unset METADATA_ATTRIBUTION METADATA_DESCRIPTION METADATA_NAME METADATA_VERSION MIN_ZOOM MAX_ZOOM BBOX CENTER_ZOOM
  mbtiles-tools meta-all "$MBTILES_FILE"
  echo "----------------------- mbtiles-tools meta-copy with auto-minmax"
  mbtiles-tools meta-copy "$MBTILES_FILE" "$MBTILES2_FILE" --auto-minmax --show-ranges
  mbtiles-tools meta-get "$MBTILES2_FILE" minzoom
  mbtiles-tools meta-get "$MBTILES2_FILE" maxzoom
  echo "----------------------- mbtiles-tools tile 1/1/0"
  mbtiles-tools tile "$MBTILES_FILE" 1/1/0
  echo "----------------------- mbtiles-tools tile 1/1/0 --summary"
  mbtiles-tools tile "$MBTILES_FILE" 1/1/0 --summary
  echo "----------------------- mbtiles-tools tile 1/1/0 --show-names"
  mbtiles-tools tile "$MBTILES_FILE" 1/1/0 --show-names
  echo "----------------------- mbtiles-tools tile 1/1/0 --show-names --summary"
  mbtiles-tools tile "$MBTILES_FILE" 1/1/0 --show-names --summary
  echo "----------------------- mbtiles-tools find-dups"
  mbtiles-tools find-dups "$MBTILES_FILE" --min-dups=2
  echo "----------------------- mbtiles-tools impute"
  mbtiles-tools impute "$MBTILES_FILE" --zoom=2 --min-dups=2 --output -
  mbtiles-tools meta-all "$MBTILES_FILE" --show-ranges
  echo "----------------------- mbtiles-tools copy"
  mbtiles-tools copy "$MBTILES_FILE" "$MBTILES3_FILE" --minzoom=1 --maxzoom=2 --reset --auto-minmax --show-ranges --verbose
  echo "----------------------- mbtiles-tools copy bbox"
  mbtiles-tools copy "$MBTILES3_FILE" "$MBTILES4_FILE" --bbox '20.2403,35.8223,23.3262,45.8046' --reset --auto-minmax --show-ranges --verbose

} > /omt/build/mbtiles.out


echo "++++++++++++++++++++++++"
echo "Running python tests"
echo "++++++++++++++++++++++++"

python -m unittest discover 2>&1 | \
	awk -v s="Ran 0 tests in" '$$0~s{print; print "\n*** No Python unit tests found, aborting"; exit(1)} 1'

echo "Done with the testing"
