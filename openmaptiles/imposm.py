from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from .tileset import Tileset

import sys
import re


def zres(pixel_scale,zoom):
    return 40075016.6855785/((1.0*pixel_scale)*2**zoom) # See https://github.com/mapbox/postgis-vt-util/blob/master/src/ZRes.sql

def call_zres(pixel_scale,match):
    return str(zres(float(pixel_scale),float(match.group(0)[7:9]))) # See https://github.com/mapbox/postgis-vt-util/blob/master/src/ZRes.sql

def create_imposm3_mapping(tileset_filename):
    tileset = Tileset.parse(tileset_filename)
    definition = tileset.definition

    pixel_scale = tileset.definition['pixel_scale']

    generalized_tables = {}
    tables = {}
    tags = {}

    for layer in tileset.layers:
        for mapping in layer.imposm_mappings:
            for table_name, definition in mapping.get('generalized_tables', {}).items():
                if 'tolerance' in definition:
                    try:					# Test if numeric
                        float(definition['tolerance'])
                    except:
                        if re.match(r"^ZRES\d{1,2}$", definition['tolerance']):
                            zoom = definition['tolerance'][4:6]
                            definition['tolerance'] = zres(float(pixel_scale),float(zoom))	# Convert to distance
                        else:
                            raise SyntaxError('Unrecognized tolerance '+str(definition['tolerance']))
                if 'sql_filter' in definition:
                   definition['sql_filter'] = re.sub(r"ZRES\d{1,2}",lambda match: call_zres(pixel_scale,match),definition['sql_filter'])
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
