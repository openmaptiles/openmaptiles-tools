import collections

from .tileset import Tileset, Layer

DbParams = collections.namedtuple('DbParams',
                                  ['dbname', 'host', 'port', 'password', 'user'])


def generate_tm2source(tileset_filename, db_params):
    tileset = Tileset.parse(tileset_filename)

    tm2 = {
        'attribution': tileset.attribution,
        'center': tileset.center,
        'bounds': tileset.bounds,
        'description': tileset.description,
        'maxzoom': tileset.maxzoom,
        'minzoom': tileset.minzoom,
        'name': tileset.name,
        'pixel_scale': tileset.pixel_scale,
        'Layer': [],
    }

    for layer in tileset.layers:
        tm2layer = generate_layer(layer, db_params)
        tm2['Layer'].append(tm2layer)

    return tm2


def generate_layer(layer: Layer, db_params):
    return {
        'id': layer.id,
        'srs': layer.srs,
        'properties': {
            'buffer-size': layer.buffer_size,
        },
        'Datasource': {
            'extent': [-20037508.34, -20037508.34, 20037508.34, 20037508.34],
            'geometry_field': layer.geometry_field,
            'key_field': layer.key_field or '',
            'key_field_as_attribute': layer.key_field_as_attribute,
            'max_size': layer.max_size,
            'port': db_params.port,
            'srid': layer.srid,
            'table': layer.query,
            'type': 'postgis',
            'host': db_params.host,
            'dbname': db_params.dbname,
            'user': db_params.user,
            'password': db_params.password,
        }
    }
