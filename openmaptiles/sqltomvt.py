import re

from typing import Iterable, Tuple, Dict, Set, Union, List, Callable

from asyncpg import Connection
# noinspection PyProtectedMember
from docopt import DocoptExit

from openmaptiles.consts import PIXEL_SCALE
from openmaptiles.tileset import Tileset, Layer
from openmaptiles.utils import find_duplicates


class MvtGenerator:
    layer_ids: Set[str]
    exclude_layers: bool  # if True, inverses layer_ids to use all except them

    def __init__(self, tileset: Union[str, Tileset], postgis_ver: str,
                 zoom: Union[str, int], x: Union[str, int], y: Union[str, int],
                 layer_ids: List[str] = None, exclude_layers=False,
                 key_column=False, gzip: Union[int, bool] = False,
                 use_feature_id: bool = None, test_geometry=False, extent=4096):
        if isinstance(tileset, str):
            self.tileset = Tileset.parse(tileset)
        else:
            self.tileset = tileset
        self.extent = extent
        self.pixel_width = PIXEL_SCALE
        self.pixel_height = PIXEL_SCALE
        self.key_column = key_column
        self.gzip = gzip
        self.test_geometry = test_geometry
        self.set_layer_ids(layer_ids, exclude_layers)
        self.zoom = zoom
        self.x = x
        self.y = y

        # extract the actual version number
        # ...POSTGIS="2.4.8 r17696"...
        m = re.search(r'POSTGIS="([^"]+)"', postgis_ver)
        ver = m[1] if m else postgis_ver
        m = re.match(r'^(?P<major>\d+)\.(?P<minor>\d+)'
                     r'(\.(?P<patch>\d+)(?P<suffix>[^ ]*)?)?', ver)
        if not m:
            raise ValueError(f"Unparseable PostGIS version string '{postgis_ver}'")
        major = int(m['major'])
        minor = int(m['minor'])
        patch = int(m['patch']) if m['patch'] else 0
        if m['suffix'] != '':
            patch -= 1
        self.postgis_ver = (major, minor, patch)

        if self.postgis_ver < (3, 0):
            if use_feature_id:
                raise ValueError(f"Feature ID is only available in PostGIS v3.0+")
            self.use_feature_id = False
            self.tile_envelope = 'TileBBox'
        else:
            self.tile_envelope = 'ST_TileEnvelope'
            self.use_feature_id = True if use_feature_id is None else use_feature_id
        self.tile_envelope_margin = False

    def set_layer_ids(self, layer_ids: List[str], exclude_layers=False):
        if exclude_layers and not layer_ids:
            raise ValueError("Cannot invert layer selection if no layer ids are given")
        if layer_ids:
            dups = find_duplicates(layer_ids)
            if dups:
                raise ValueError(f"Duplicate layer IDs: {', '.join(dups)}")
        self.layer_ids = set(layer_ids or [])
        self.exclude_layers = exclude_layers

    def generate_sqltomvt_func(self, fname):
        """
        Creates a SQL function that returns a single bytea value or null
        """
        return f"""\
DROP FUNCTION IF EXISTS {fname}(integer, integer, integer);
CREATE FUNCTION {fname}(zoom integer, x integer, y integer)
RETURNS {'TABLE(mvt bytea, key text)' if self.key_column else 'bytea'} AS $$
{self.generate_sql()};
$$ LANGUAGE SQL STABLE RETURNS NULL ON NULL INPUT;"""

    def generate_sqltomvt_preparer(self, fname):
        """
        Creates a SQL prepared statement returning 0 or 1 row with a single mvt column.
        """
        return f"""\
-- Delete prepared statement if it already exists
DO $$ BEGIN
IF EXISTS (SELECT * FROM pg_prepared_statements where name = '{fname}') THEN
  DEALLOCATE {fname};
END IF;
END $$;

-- Run this statement with   EXECUTE {fname}(zoom, x, y)
PREPARE {fname}(integer, integer, integer) AS
{self.generate_sql()};"""

    def generate_sql(self):
        queries = []
        for layer_id, layer in self.get_layers():
            queries.append(self.generate_layer(layer))

        extras = ''
        if self.test_geometry:
            extras += f', SUM(COALESCE(bad_geos, 0)) as bad_geos'

        concatenate_layers = "STRING_AGG(mvtl, '')"
        # Handle when gzip is True or a number
        # Note that any bool is an int, but not reverse: isinstance(False, int) == True
        if not isinstance(self.gzip, bool) or self.gzip:
            # GZIP function is available from https://github.com/pramsey/pgsql-gzip
            if isinstance(self.gzip, bool):
                concatenate_layers = f"GZIP({concatenate_layers})"
            else:
                self.gzip = int(self.gzip)
                assert 0 <= self.gzip <= 9
                concatenate_layers = f"GZIP({concatenate_layers}, {self.gzip})"
        union_layers = "\n    UNION ALL\n  ".join(queries)
        query = f"""\
SELECT {concatenate_layers} AS mvt{extras} FROM (
  {union_layers}
) AS all_layers"""

        if self.key_column:
            query = f"SELECT mvt, md5(mvt) AS key" \
                    f"{', bad_geos' if self.test_geometry else ''} " \
                    f"FROM ({query}) AS mvt_data"

        return query + '\n'

    def generate_layer(self, layer: Layer):
        """
        Convert layer definition into a SQL statement.
        """
        columns = None
        if self.test_geometry:
            columns = f"(1-ST_IsValid({layer.geometry_field})::int) as bad_geos"
        query = self.layer_to_query(layer, extra_columns=columns)

        extras = ''
        if self.test_geometry:
            # Count the number of invalid regular & mvt geometries (should always be 0)
            extras += f', SUM((1' \
                      f'-COALESCE(ST_IsValid(mvtgeometry)::int, 1))' \
                      f'+COALESCE(bad_geos, 0)' \
                      f') as bad_geos'

        # PostGIS < v3 did not support feature_ids
        # TODO: remove key field (osm_id) from query result to prevent
        # it being used as a regular attribute
        key_fld = layer.key_field if self.use_feature_id else None

        # Combine all layer's features into a single MVT blob representing one layer
        as_mvt_params = f"'{layer.id}', {self.extent}, 'mvtgeometry'"
        if self.postgis_ver < (2, 4, 0):
            # OMT for a long time used PostGIS 2.4.0dev r15415 with legacy param order
            # ST_AsMVT(text name, integer extent, text geom_name, anyelement row)
            as_mvt_params = f"{as_mvt_params}, t"
        else:
            # ST_AsMVT(anyelement row, text name, integer extent, text geom_name)
            as_mvt_params = f"t, {as_mvt_params}"

        query = f"""\
SELECT \
COALESCE(ST_AsMVT({as_mvt_params}{f", '{key_fld}'" if key_fld else ""}), '') \
as mvtl{extras} FROM {query}"""

        if self.postgis_ver < (2, 5):
            # ST_AsMVTGeom returned NULL for some geometries,
            # ignore them to avoid ST_AsMVT errors
            query += ' WHERE mvtgeometry IS NOT NULL'

        return query

    def layer_to_query(self,
                       layer: Layer,
                       to_mvt_geometry=True,
                       mvt_geometry_wrapper: Callable[[str], str] = None,
                       extra_columns: str = None) -> str:
        query = layer.query
        if self.zoom is not None:
            query = self.substitute_sql(query, layer, self.zoom, self.x, self.y)

        replacement = ''
        if to_mvt_geometry:
            replacement = f"ST_AsMVTGeom(" \
                          f"{layer.geometry_field}, " \
                          f"{self.bbox(self.zoom, self.x, self.y)}, " \
                          f"{self.extent}, " \
                          f"{layer.buffer_size}, " \
                          f"true)"
            if mvt_geometry_wrapper:
                replacement = mvt_geometry_wrapper(replacement)
            replacement += " AS mvtgeometry"
        if extra_columns:
            if replacement:
                replacement += ', '
            replacement += extra_columns

        if replacement:
            q = query.replace(layer.geometry_field, replacement)
            if len(q) - len(replacement) + len(layer.geometry_field) != len(query):
                raise ValueError(
                    f"Unable to replace '{layer.geometry_field}' in {layer.id} layer, "
                    f"expected a single geometry field in the layer query definition")
            query = q

        return query

    def bbox(self, zoom, x, y, margin=None):
        margin_str = '' if margin is None else f", {margin}"
        return f"{self.tile_envelope}({zoom}, {x}, {y}{margin_str})"

    def substitute_sql(self, query, layer: Layer, zoom, x, y):
        # A zoom 0 tile has width/height of 40075016.6855785 units
        # Buffer expressed as a percentage of a tile width gives us this formula.
        # Every subsequent zoom divides it by 2
        if layer.buffer_size > 0:
            if not self.tile_envelope_margin:
                percentage = 40075016.6855785 * layer.buffer_size / self.extent
                bbox = f"ST_Expand({self.bbox(zoom, x, y)}, {percentage}/2^{zoom})"
            else:
                # Once https://github.com/postgis/postgis/pull/514 is merged
                bbox = self.bbox(zoom, x, y, float(layer.buffer_size) / self.extent)
        else:
            bbox = self.bbox(zoom, x, y)

        query = (query
                 .replace("!bbox!", bbox)
                 .replace("z(!scale_denominator!)", str(zoom))
                 .replace("!pixel_width!", str(self.pixel_width))
                 .replace("!pixel_height!", str(self.pixel_height)))
        if '!scale_denominator!' in query:
            raise ValueError(
                'MVT made an invalid assumption that "!scale_denominator!" is '
                'always used as a parameter to z() function. Either change '
                'the layer queries, or fix this code')
        return query

    async def validate_layer_fields(
        self, connection: Connection, layer_id: str, layer: Layer
    ) -> Dict[str, str]:
        """Validate that fields in the layer definition match the ones
        returned by the dummy (0-length) SQL query.
        Returns field names => SQL types (oid) excluding the geometry field"""
        query_field_map = await self.get_sql_fields(connection, layer)
        layer_fields = set(layer.get_fields())

        # Make sure query returns expected geometry field
        geom_fld = layer.geometry_field
        if geom_fld not in query_field_map:
            raise ValueError(
                f"Layer '{layer_id}' query does not generate expected '{geom_fld}'"
                f"{' (geometry)' if geom_fld != 'geometry' else ''} field")
        del query_field_map[geom_fld]

        # compare query result fields with declared ones
        query_fields = set(query_field_map.keys())
        if layer_fields != query_fields:
            same = layer_fields.intersection(query_fields)
            layer_fields -= same
            query_fields -= same
            error = f"Declared fields in layer '{layer_id}' do not match " \
                    f"the fields received from a query:\n"
            if layer_fields:
                error += f"  These fields were declared, but not returned by " \
                         f"the query: {', '.join(layer_fields)}"
            if query_fields:
                error += f"  These fields were returned by the query, " \
                         f"but not declared: {', '.join(query_fields)}"
            raise ValueError(error)

        return query_field_map

    async def get_sql_fields(
        self, connection: Connection, layer: Layer
    ) -> Dict[str, str]:
        """Get field names => SQL types (oid) by executing a dummy query"""
        query = self.substitute_sql(layer.query, layer, 0, 0, 0)
        st = await connection.prepare(f"SELECT * FROM {query} WHERE false LIMIT 0")
        return {fld.name: fld.type.oid for fld in st.get_attributes()}

    def get_layers(self) -> Iterable[Tuple[str, Layer]]:
        all_layers = [(v.id, v) for v in self.tileset.layers]
        if not all_layers:
            raise DocoptExit('Could not find any layer definitions')
        duplicates = find_duplicates([k for k, v in all_layers])
        if duplicates:
            raise DocoptExit(f'Duplicate layer IDs found: {", ".join(duplicates)}')
        if not self.layer_ids:
            yield from all_layers
            return
        found_layers = set()
        skipped_layers = set()
        for layer_id, layer in all_layers:
            if (layer_id in self.layer_ids) != self.exclude_layers:
                found_layers.add(layer_id)
                yield layer_id, layer
            else:
                skipped_layers.add(layer_id)
        expected_result = skipped_layers if self.exclude_layers else found_layers
        if self.layer_ids != expected_result:
            unknown = sorted(self.layer_ids - expected_result)
            raise DocoptExit(
                f"Unable to find layer [{', '.join(unknown)}]. Available layers:\n" +
                '\n'.join(f"* {k}" + (
                    f"\n{v.description}" if v.description else ''
                ) for k, v in all_layers)
            )
