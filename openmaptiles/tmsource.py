from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import collections

from .tileset import Tileset
from .language import languages_to_sql


DbParams = collections.namedtuple('DbParams', ['dbname', 'host', 'port',
                                               'password', 'user'])


def generate_tm2source(tileset_filename, db_params):
    tileset = Tileset.parse(tileset_filename)

    layer_defaults = tileset['defaults']
    tm2 = {
        'attribution': tileset['attribution'],
        'center': tileset['center'],
        'bounds': tileset['bounds'],
        'description': tileset['description'],
        'maxzoom': tileset['maxzoom'],
        'minzoom': tileset['minzoom'],
        'name': tileset['name'],
        'pixel_scale': tileset['pixel_scale'],
        'Layer': [],
    }

    definition = tileset.definition
    name_languages = languages_to_sql(definition.get('languages', []))

    query_tokens = {
        'name_languages': name_languages
    }

    for layer in tileset.layers:
        tm2layer = generate_layer(layer, layer_defaults, query_tokens, db_params)
        tm2['Layer'].append(tm2layer)

    return tm2


def generate_layer(layer_def, layer_defaults, query_tokens, db_params):
    layer = layer_def['layer']
    datasource = layer['datasource']

    query = datasource['query'].format(**query_tokens)

    tm2layer = {
        'id': layer['id'],
        'srs': layer.get('srs', layer_defaults['srs']),
        'properties': {
            'buffer-size': layer['buffer_size']
        },
        'Datasource': {
          'extent': [-20037508.34, -20037508.34, 20037508.34, 20037508.34],
          'geometry_field': datasource.get('geometry_field', 'geometry'),
          'key_field': datasource.get('key_field', ''),
          'key_field_as_attribute': datasource.get('key_field_as_attribute', ''),
          'max_size': datasource.get('max_size', 512),
          'port': db_params.port,
          'srid': datasource.get('srid', layer_defaults['datasource']['srid']),
          'table': query,
          'type': 'postgis',
          'host': db_params.host,
          'dbname': db_params.dbname,
          'user': db_params.user,
          'password': db_params.password,
        }
    }
    return tm2layer
