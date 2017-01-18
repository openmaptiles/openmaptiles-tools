from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from .tileset import Tileset


def create_imposm3_mapping(tileset_filename):
    tileset = Tileset.parse(tileset_filename)
    definition = tileset.definition

    generalized_tables = {}
    tables = {}
    tags = {}

    for layer in tileset.layers:
        for mapping in layer.imposm_mappings:
            for table_name, definition in mapping.get('generalized_tables', {}).items():
                generalized_tables[table_name] = definition
            for table_name, definition in mapping.get('tables', {}).items():
                tables[table_name] = definition
            for tag_name, definition in mapping.get('tags', {}).items():
                tags[tag_name] = definition

    return {
        'tags': tags,
        'generalized_tables': generalized_tables,
        'tables': tables,
    }
