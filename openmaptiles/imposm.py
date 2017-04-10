from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from .tileset import Tileset

import sys
import re

def ZRes(z):
    return 40075016.6855785/(256*2**z) # See https://github.com/mapbox/postgis-vt-util/blob/master/src/ZRes.sql

def create_imposm3_mapping(tileset_filename):
    tileset = Tileset.parse(tileset_filename)
    definition = tileset.definition

    generalized_tables = {}
    tables = {}
    tags = {}

    for layer in tileset.layers:
        for mapping in layer.imposm_mappings:
            for table_name, definition in mapping.get('generalized_tables', {}).items():
                if 'tolerance' in definition:
                    try:
                        float(definition['tolerance'])
                        generalized_tables[table_name] = definition
                    except:
                        if re.match(r"^Z\d{1,2}$", definition['tolerance']):
                            definition['tolerance'] = ZRes(float(definition['tolerance'][1:3]))
                            generalized_tables[table_name] = definition
                        else:
                            raise SyntaxError('Unrecognized tolerance '+str(definition['tolerance']))
            for table_name, definition in mapping.get('tables', {}).items():
                tables[table_name] = definition
            for tag_name, definition in mapping.get('tags', {}).items():
                tags[tag_name] = definition

    return {
        'tags': tags,
        'generalized_tables': generalized_tables,
        'tables': tables,
    }
