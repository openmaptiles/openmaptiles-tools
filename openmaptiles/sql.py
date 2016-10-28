from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from .tileset import Tileset


def collect_sql(tileset_filename):
    tileset = Tileset.parse(tileset_filename)
    sql = ''
    for layer in tileset.layers:
        sql += layer_notice(layer['layer']['id'])
        for schema in layer.schemas:
            sql += schema
    return sql


def layer_notice(layer_name):
    return "DO $$ BEGIN RAISE NOTICE 'Layer {0}'; END$$;".format(layer_name)
