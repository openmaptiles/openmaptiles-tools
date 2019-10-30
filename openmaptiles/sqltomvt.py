from .consts import PIXEL_SCALE
from .language import languages_to_sql
from .tileset import Tileset
from docopt import DocoptExit


class MvtGenerator:
    def __init__(self, tileset, mask_layer=None, mask_zoom=8, layer_ids=None):
        if isinstance(tileset, str):
            self.tileset = Tileset.parse(tileset)
        else:
            self.tileset = tileset
        self.mask_layer = mask_layer
        self.mask_zoom = mask_zoom
        self.extent = 4096
        self.pixel_width = PIXEL_SCALE
        self.pixel_height = PIXEL_SCALE
        self.layers_ids = set(layer_ids or [])

    def generate_sqltomvt_func(self, fname):
        """
        Creates a SQL function that returns a single bytea value or null
        """
        return f"""\
CREATE OR REPLACE FUNCTION {fname}(zoom integer, x integer, y integer)
RETURNS bytea AS $$
{self.generate_query("TileBBox(zoom, x, y)", "zoom")};
$$ LANGUAGE SQL STABLE RETURNS NULL ON NULL INPUT;"""

    def generate_sqltomvt_preparer(self, fname):
        """
        Creates a SQL prepared statement that returns 0 or 1 row with a single mvt column.
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
{self.generate_sqltomvt_query()};"""

    def generate_sqltomvt_query(self):
        return self.generate_query("TileBBox($1, $2, $3)", "$1")

    def generate_sqltomvt_psql(self):
        return self.generate_query("TileBBox(:zoom, :x, :y)", ":zoom")

    def generate_sqltomvt_raw(self):
        return self.generate_query(None, None)

    def generate_query(self, bbox, zoom):
        queries = []
        found_layers = set()
        for layer in self.tileset.layers:
            layer_id = layer["layer"]['id']
            if self.layers_ids and layer_id not in self.layers_ids:
                continue
            found_layers.add(layer_id)
            # If mask-layer is set (e.g. to 'water'), add an extra column 'IsEmpty'
            # to each layer's result row. For non-water or water in zoom <= mask-zoom,
            # always set it to FALSE. For zoom > mask-zoom, test if the polygon spanning
            # the entire tile is fully within layer's geometry
            if not self.mask_layer:
                empty_zoom = False
            elif layer_id == self.mask_layer:
                empty_zoom = self.mask_zoom
            else:
                empty_zoom = True
            query = self.generate_layer(layer, zoom, empty_zoom, bbox)
            queries.append(query)
        if self.layers_ids and self.layers_ids != found_layers:
            unknown = sorted(self.layers_ids - found_layers)
            raise DocoptExit(
                f"Unable to find layer [{', '.join(unknown)}]. Available layers:\n" +
                '\n'.join(f"* {v['layer']['id']}" + (
                    f"\n{v['layer']['description']}" if v['layer'].get('description')
                    else ''
                ) for v in self.tileset.layers)
            )
        if not queries:
            raise DocoptExit('Could not find any layer definitions')

        from_clause = "FROM (\n  " + \
                      "\n    UNION ALL\n  ".join(queries) + "\n) AS all_layers\n"

        # If mask-layer is set, wrap query to detect when the IsEmpty column
        # is TRUE (for water), and there are no other rows, and if so, return nothing.
        if self.mask_layer:
            from_clause = (
                "FROM (\n" +
                "SELECT IsEmpty, count(*) OVER () AS LayerCount, mvtl " +
                from_clause +
                ") AS counter_layers\n" +
                "HAVING BOOL_AND(NOT IsEmpty OR LayerCount <> 1)")

        query = "SELECT STRING_AGG(mvtl, '') AS mvt " + from_clause

        return query

    def generate_layer(self, layer_def, zoom, empty_zoom, bbox):
        """
        If empty_zoom is True, adds an extra sql column with a constant value,
        otherwise if it is an integer, tests if the geometry of this layer covers the whole
        tile, and outputs true/false, otherwise no extra column is added
        """
        layer = layer_def["layer"]
        query = layer['datasource']['query']
        has_languages = '{name_languages}' in query
        if has_languages:
            languages = self.tileset.definition.get('languages', [])
            query = query.format(name_languages=languages_to_sql(languages))
        buffer = layer['buffer_size']

        if query.startswith("("):
            # Remove the first and last parenthesis and "AS t"
            query = query[1:query.rfind(")")]

        ext = self.extent
        query = query.replace(
            "geometry",
            f"ST_AsMVTGeom(geometry, !bbox!, {ext}, {buffer}, true) AS mvtgeometry")

        if isinstance(empty_zoom, bool):
            is_empty = "FALSE AS IsEmpty, " if empty_zoom else ""
        else:
            # Test that geometry covers the whole tile
            zero = 0
            wkt_polygon = f"POLYGON(({zero} {ext},{zero} {zero},{ext} {zero},{ext} {ext},{zero} {ext}))"
            is_empty = f"""\
CASE {zoom} <= {empty_zoom} \
WHEN TRUE THEN FALSE \
ELSE ST_WITHIN(ST_GeomFromText('{wkt_polygon}', 3857), ST_UNION(mvtgeometry)) \
END AS IsEmpty, """

        # Combine all layer's features into a single MVT blob representing one layer
        # only if the MVT geometry is not NULL
        # Skip the whole layer if there is nothing in it
        query = f"""\
SELECT {is_empty}ST_AsMVT(tile, '{layer['id']}', {ext}, 'mvtgeometry') as mvtl \
FROM ({query} WHERE ST_AsMVTGeom(geometry, !bbox!, {ext}, {buffer}, true) IS NOT NULL) AS tile \
HAVING COUNT(*) > 0"""

        if bbox:
            query = (query
                     .replace("!bbox!", bbox)
                     .replace("z(!scale_denominator!)", zoom)
                     .replace("!pixel_width!", str(self.pixel_width))
                     .replace("!pixel_height!", str(self.pixel_height)))
            if '!scale_denominator!' in query:
                raise ValueError(
                    'MVT made an invalid assumption that "!scale_denominator!" is '
                    'always used as a parameter to z() function. Either change '
                    'the layer queries, or fix this code')
        return query
