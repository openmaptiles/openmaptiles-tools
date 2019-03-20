from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import collections

from .tileset import Tileset
from .language import languages_to_sql


def generate_sqltomvt(tileset_filename):
    tileset = Tileset.parse(tileset_filename)

    query_tokens = {
        'name_languages': languages_to_sql(tileset.definition.get('languages', []))
    }

    extent = 4096
    queries = [generate_layer(layer, query_tokens, extent) for layer in tileset.layers]

    query = "PREPARE gettile(geometry, numeric, numeric, numeric) AS\n\n" + \
            "SELECT STRING_AGG(mvt) FROM (\n  " + \
            "\n    UNION ALL\n  ".join(queries) + \
            "\n) AS ua;"

    return (query
            .replace("!bbox!", "$1")
            .replace("!scale_denominator!", "$2")
            .replace("!pixel_width!", "$3")
            .replace("!pixel_height!", "$4"))

    # SELECT data, flag
    # FROM (SELECT data, flag,
    #              count(*) OVER () AS c
    # FROM (SELECT ...) AS src
    # ) AS q
    # WHERE NOT flag OR c <> 1;


def generate_layer(layer_def, query_tokens, extent):
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

    query = (
        # Combine all layer's features into a single MVT tile
        "SELECT ST_AsMVT(tile, '{id}', {extent}, 'mvtgeometry') as mvt "
        # only if the MVT geometry is not NULL
        "FROM ({query} WHERE ST_AsMVTGeom(geometry, !bbox!, {extent}, {buffer}, true) IS NOT NULL) AS tile "
        # Skip the whole layer if there is nothing in it
        "HAVING COUNT(*) > 0"
    ).format(id=layer['id'], extent=extent, query=query, buffer=buffer)

    return query
