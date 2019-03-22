from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import collections

from .tileset import Tileset
from .language import languages_to_sql


def generate_sqltomvt_func(opts):
    header = """
CREATE OR REPLACE FUNCTION {0}(zoom integer, x integer, y integer)
RETURNS TABLE(mvt bytea) AS $$
""".format(opts['fname']).lstrip()

    query = generate_query(opts, "TileBBox(zoom, x, y)", "zoom")
    footer = ";\n$$ LANGUAGE SQL IMMUTABLE;"
    return header + query + footer


def generate_sqltomvt_preparer(opts):
    header = """
-- Delete prepared statement if it already exists
DO $$ BEGIN
IF EXISTS (SELECT * FROM pg_prepared_statements where name = '{0}') THEN
  DEALLOCATE {0};
END IF;
END $$;

-- Run this statement with   EXECUTE {0}(zoom, x, y)
PREPARE {0}(integer, integer, integer) AS
""".format(opts['fname']).lstrip()

    return header + generate_query(opts, "TileBBox($1, $2, $3)", "$1") + ";"


def generate_sqltomvt_raw(opts):
    return generate_query(opts, None, None, None)


def generate_query(opts, bbox, zoom):
    tileset = Tileset.parse(opts['tileset'])
    query_tokens = {
        'name_languages': languages_to_sql(tileset.definition.get('languages', []))
    }
    extent = 4096
    pixel_width = 256
    pixel_height = 256

    queries = []
    for layer in tileset.layers:
        if not opts['mask-layer']:
            empty_zoom = False
        elif layer["layer"]['id'] == opts['mask-layer']:
            empty_zoom = opts['mask-level']
        else:
            empty_zoom = True
        queries.append(generate_layer(layer, query_tokens, extent, empty_zoom))

    from_clause = "FROM (\n  " + "\n    UNION ALL\n  ".join(queries) + "\n) AS all_layers\n"

    if opts['mask-layer']:
        from_clause = "FROM (\nSELECT IsEmpty, count(*) OVER () AS LayerCount, mvtl " + from_clause + ") AS counter_layers\n"

    query = "SELECT STRING_AGG(mvtl, '') AS mvt " + from_clause

    if opts['mask-layer']:
        query += "HAVING BOOL_AND(NOT IsEmpty OR LayerCount <> 1)"

    if bbox is None:
        return query

    query = (query
             .replace("!bbox!", bbox)
             .replace("z(!scale_denominator!)", zoom)
             .replace("!pixel_width!", str(pixel_width))
             .replace("!pixel_height!", str(pixel_height)))

    if '!scale_denominator!' in query:
        raise ValueError('We made invalid assumption that "!scale_denominator!" is always used '
                         'as a parameter to z() function. Either change the layer queries, or fix this code')

    return query


def generate_layer(layer_def, query_tokens, extent, empty_zoom):
    """
    If empty_zoom is True, adds an extra sql column with a constant value,
    otherwise if it is an integer, tests if the geometry of this layer covers the whole tile, and outputs true/false,
    otherwise no extra column is added
    """
    layer = layer_def["layer"]
    buffer = layer['buffer_size']
    query = layer["datasource"]["query"].format(**query_tokens)

    if query.startswith("("):
        # Remove the first and last parentesis and "AS t"
        query = query[1:query.rfind(")")]

    # TODO: Once fully migrated to Python 3.6+, use f-strings instead
    query = query.replace(
        "geometry",
        "ST_AsMVTGeom(geometry, !bbox!, {extent}, {buffer}, true) AS mvtgeometry".format(extent=extent, buffer=buffer))

    if empty_zoom == False:
        filter = ""
    elif empty_zoom == True:
        filter = "FALSE AS IsEmpty, "
    else:
        # Test that geometry covers the whole tile
        wkt_polygon = "POLYGON(({0} {1},{0} {0},{1} {0},{1} {1},{0} {1}))".format(0, extent)
        filter = ("CASE z(!scale_denominator!) <= {0} "
                  "WHEN TRUE THEN FALSE "
                  "ELSE ST_WITHIN(ST_GeomFromText('{1}', 3857), ST_UNION(mvtgeometry)) "
                  "END AS IsEmpty, ".format(empty_zoom, wkt_polygon))

    query = (
            "SELECT " + filter +
            # Combine all layer's features into a single MVT blob representing one layer
            "ST_AsMVT(tile, '{id}', {extent}, 'mvtgeometry') as mvtl "
            # only if the MVT geometry is not NULL
            "FROM ({query} WHERE ST_AsMVTGeom(geometry, !bbox!, {extent}, {buffer}, true) IS NOT NULL) AS tile "
            # Skip the whole layer if there is nothing in it
            "HAVING COUNT(*) > 0"
    ).format(id=layer['id'], extent=extent, query=query, buffer=buffer)

    return query
