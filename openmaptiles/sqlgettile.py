from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import collections

from .tileset import Tileset
from .language import languages_to_sql


def generate_sqlgettile(tileset_filename):
    tileset = Tileset.parse(tileset_filename)

    query_tokens = {
        'name_languages': languages_to_sql(tileset.definition.get('languages', []))
    }

    extent = 4096
    queries = [generate_layer(layer, query_tokens, extent) for layer in tileset.layers]

    return "PREPARE gettile(geometry, numeric, numeric, numeric) AS \n" + \
           "\n   UNION ALL\n".join(queries) + "\n;"


def generate_layer(layer_def, query_tokens, extent):
    layer = layer_def["layer"]
    buffer = layer['buffer_size']
    query = layer["datasource"]["query"].format(**query_tokens)

    if query.startswith("("):
        # Remove the first and last parentesis and "AS t"
        query = query[1:query.rfind(")")]

    query = query.replace(
        "geometry",
        "ST_AsMVTGeom(geometry, !bbox!, {extent}, {buffer}, true) AS mvtgeometry"
            .format(extent=extent, buffer=buffer))

    query = (
        "SELECT ST_AsMVT(tile, '{id}', {extent}, 'mvtgeometry') FROM ({query} WHERE ST_AsMVTGeom(geometry, !bbox!, {extent}, {buffer}, true) IS NOT NULL) AS tile"
        .format(id=layer['id'], extent=extent, query=query, buffer=buffer))

    query = (query
             .replace("!bbox!", "$1")
             .replace("!scale_denominator!", "$2")
             .replace("!pixel_width!", "$3")
             .replace("!pixel_height!", "$4"))

    return query
