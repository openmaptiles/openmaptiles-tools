import sys
from typing import Tuple, List

import yaml
import os.path
import codecs


class Layer:
    @staticmethod
    def parse(layer_filename):
        layer = parse_file(layer_filename)

        def iterate_imposm_mapping_files():
            for data_source in layer.get('datasources', []):
                if data_source['type'] != 'imposm3':
                    continue
                mapping_path = data_source['mapping_file']
                if not os.path.isabs(mapping_path):
                    mapping_path = os.path.join(
                        os.path.dirname(layer_filename),
                        mapping_path
                    )
                yield mapping_path

        def parse_imposm_mappings():
            for mapping_path in iterate_imposm_mapping_files():
                yield parse_file(mapping_path)

        def parse_imposm_mappings_str():
            for mapping_path in iterate_imposm_mapping_files():
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

    def get_fields(self) -> List[str]:
        layer_fields = list(self['layer']['fields'].keys())
        if self.key_field:
            layer_fields.append(self.key_field)
        return layer_fields

    @property
    def key_field(self) -> str:
        source = self['layer']['datasource']
        result = source['key_field'] if 'key_field' in source else None
        if result:
            val = source.get('key_field_as_attribute')
            if val and val != 'no':
                # If 'yes', we will need to generate a wrapper query that includes
                # osm_id column twice - once for feature_id, and once as an attribute
                raise ValueError(f"key_field_as_attribute={val} is not yet implemented")
        return result

    @property
    def geometry_field(self) -> str:
        source = self['layer']['datasource']
        result = source['geometry'] if 'geometry' in source else 'geometry'
        if result in self['layer']['fields']:
            raise ValueError(
                f"Layer '{self['layer']['id']}' must not have the implicit 'geometry' "
                f"field declared in the 'fields' section of the yaml file")
        return result


class Tileset:
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
