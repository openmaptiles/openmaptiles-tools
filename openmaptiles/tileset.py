import sys
from typing import Tuple, List

import yaml
import os.path
import codecs


class Layer(object):
    @staticmethod
    def parse(layer_filename):
        layer = parse_file(layer_filename)

        def parse_imposm_mappings():
            for data_source in layer.get('datasources', []):
                if data_source['type'] != 'imposm3':
                    continue

                mapping_path = data_source['mapping_file']
                if not os.path.isabs(mapping_path):
                    mapping_path = os.path.join(
                        os.path.dirname(layer_filename),
                        mapping_path
                    )

                yield parse_file(mapping_path)

        def parse_imposm_mappings_str():
            for data_source in layer.get('datasources', []):
                if data_source['type'] != 'imposm3':
                    continue

                mapping_path = data_source['mapping_file']
                if not os.path.isabs(mapping_path):
                    mapping_path = os.path.join(
                        os.path.dirname(layer_filename),
                        mapping_path
                    )

                with codecs.open(mapping_path, 'r', 'utf-8') as f:
                    yield f.read()

        def parse_schemas():
            for schema_path in layer.get('schema', []):
                if not os.path.isabs(schema_path):
                    schema_path = os.path.join(
                        os.path.dirname(layer_filename),
                        schema_path
                    )

                with codecs.open(schema_path, 'r', 'utf-8') as f:
                    yield f.read()

        return Layer(layer_filename, layer,
                     list(parse_imposm_mappings()),
                     list(parse_imposm_mappings_str()),
                     list(parse_schemas()))

    def __init__(self, filename, definition, mappings=None, mappings_str=None,
                 schemas=None):
        self.filename = filename
        self.definition = definition
        self.imposm_mappings = [] if mappings is None else mappings
        self.imposm_mappings_str = [] if mappings_str is None else mappings_str
        self.schemas = [] if schemas is None else schemas

    def __getitem__(self, attr):
        if attr in self.definition:
            return self.definition[attr]
        elif attr == "fields":
            return {}
        elif attr == "description":
            return ""
        else:
            raise KeyError

    def get_fields(self) -> Tuple[List[str], str]:
        layer = self['layer']
        source = layer['datasource']
        layer_fields = list(layer['fields'].keys())
        key_field = source['key_field'] if 'key_field' in source else False
        if self.geometry_field in layer_fields:
            raise ValueError(
                f"Layer '{layer['id']}' must not have the implicit 'geometry' field "
                f"declared in the 'fields' section of the yaml file")
        if key_field:
            layer_fields.append(key_field)
            if source.get('key_field_as_attribute') and \
                source['key_field_as_attribute'] != 'no':
                # If 'yes', we will need to generate a wrapper query that includes
                # osm_id column twice - once for feature_id, and once as an attribute
                raise ValueError('key_field_as_attribute=yes is not yet implemented')
        return layer_fields, key_field

    @property
    def geometry_field(self):
        source = self['layer']['datasource']
        return source['geometry'] if 'geometry' in source else 'geometry'


class Tileset(object):
    @staticmethod
    def parse(tileset_filename):
        tileset = parse_file(tileset_filename)['tileset']

        def parse_layers():
            for layer_filename in tileset['layers']:
                if not os.path.isabs(layer_filename):
                    tileset_dir = os.path.dirname(tileset_filename)
                    layer_filename = os.path.join(tileset_dir, layer_filename)

                yield Layer.parse(layer_filename)

        return Tileset(tileset_filename, tileset, list(parse_layers()))

    def __init__(self, filename, definition, layers):
        self.filename = filename
        self.definition = definition
        self.layers = layers

    def __getitem__(self, attr):
        if attr in self.definition:
            return self.definition[attr]
        else:
            raise KeyError


def parse_file(filename):
    with open(filename, 'r') as stream:
        try:
            return yaml.load(stream, Loader=yaml.FullLoader)
        except yaml.YAMLError as e:
            print('Could not parse ' + filename)
            print(e)
            sys.exit(403)
