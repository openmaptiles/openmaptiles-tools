from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from .tileset import Tileset


def collect_sql(tileset_filename):
    tileset = Tileset.parse(tileset_filename)
    sql = ''

    definition = tileset.definition
    languages = map(lambda l: str(l), definition.get('languages', []))
    sql += get_slice_language_tags(languages)

    for layer in tileset.layers:
        sql += layer_notice(layer['layer']['id'])
        for schema in layer.schemas:
            sql += schema
    return sql


def layer_notice(layer_name):
    return "DO $$ BEGIN RAISE NOTICE 'Layer {0}'; END$$;".format(layer_name)

SLICE_LANGUAGE_TAGS_SQL="""CREATE OR REPLACE FUNCTION slice_language_tags(tags hstore)
RETURNS hstore AS $$
    SELECT delete_empty_keys(slice(tags, ARRAY[{0}]))
$$ LANGUAGE SQL IMMUTABLE;
"""

def get_slice_language_tags(languages):
    include_tags = list(map(lambda l: 'name:'+l, languages))
    include_tags.append('int_name')
    include_tags.append('loc_name')
    include_tags.append('name')
    include_tags.append('wikidata')
    include_tags.append('wikipedia')

    tags_sql = "'" + "', '".join(include_tags) + "'"

    return SLICE_LANGUAGE_TAGS_SQL.format(tags_sql)
