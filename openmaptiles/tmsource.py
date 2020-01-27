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
    key_field = layer.key_field or ''
    if key_field == '':
        # weird Mapnik expectation. Use '', otherwise Mapnik throws an error:
        #   column number 4 is out of range 0..3
        #   Error: basic_string::_S_construct null not valid
        kf_as_attr = ''
    else:
        kf_as_attr = layer.key_field_as_attribute
    return {
        'id': layer.id,
        'srs': layer.srs,
        'properties': {
            'buffer-size': layer.buffer_size,
        },
        'Datasource': {
            'extent': [-20037508.34, -20037508.34, 20037508.34, 20037508.34],
            'geometry_field': layer.geometry_field,
            'key_field': key_field,
            'key_field_as_attribute': kf_as_attr,
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
