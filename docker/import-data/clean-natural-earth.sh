#!/usr/bin/env bash
set -o errexit
set -o pipefail
set -o nounset


if [[ -z "$1" || ! -f "$1" ]]; then
  echo "First parameter must be an existing sqlite3 database file"
  exit 1
fi

NATURAL_EARTH_DB=$1


# Drop all unused tables to save space and keep the schema clean
# If we only drop the geometry columns the import-external image
# doesn't get smaller so we need to remove both

function drop_table() {
    local table_name="$1"
    echo "DROP TABLE $table_name;" | sqlite3 "$NATURAL_EARTH_DB"
    echo "DELETE FROM geometry_columns WHERE f_table_name = '$table_name';" | sqlite3 "$NATURAL_EARTH_DB"
}


echo "Cleaning up $NATURAL_EARTH_DB - removing all unneeded tables. Initial size $(du -h "$NATURAL_EARTH_DB" | cut -f1)"

#
# Keep selected tables before import to the PostgreSQL database.
#
count=0
for tbl in $(echo \
  "select name from sqlite_master " \
  "WHERE type='table' AND name like 'ne%' and name not in (" \
    "'ne_10m_admin_0_boundary_lines_land'," \
    "'ne_10m_admin_0_countries'," \
    "'ne_10m_admin_0_boundary_lines_map_units'," \
    "'ne_10m_admin_1_states_provinces'," \
    "'ne_10m_admin_1_states_provinces_lines'," \
    "'ne_10m_antarctic_ice_shelves_polys'," \
    "'ne_10m_geography_marine_polys'," \
    "'ne_10m_glaciated_areas'," \
    "'ne_10m_lakes'," \
    "'ne_10m_ocean'," \
    "'ne_10m_populated_places'," \
    "'ne_50m_admin_0_boundary_lines_land'," \
    "'ne_50m_antarctic_ice_shelves_polys'," \
    "'ne_50m_glaciated_areas'," \
    "'ne_50m_lakes'," \
    "'ne_50m_ocean'," \
    "'ne_50m_rivers_lake_centerlines'," \
    "'ne_50m_urban_areas'," \
    "'ne_110m_admin_0_boundary_lines_land'," \
    "'ne_110m_glaciated_areas'," \
    "'ne_110m_lakes'," \
    "'ne_110m_ocean'," \
    "'ne_110m_rivers_lake_centerlines'" \
  ");" | sqlite3 "$NATURAL_EARTH_DB" ); do

  drop_table "$tbl"
  count=$((count+1))

done

echo "$count tables have been dropped from $NATURAL_EARTH_DB, vacuuming..."
echo "VACUUM;" | sqlite3 "$NATURAL_EARTH_DB"
echo "Done with $NATURAL_EARTH_DB -- final size $(du -h "$NATURAL_EARTH_DB" | cut -f1)"
