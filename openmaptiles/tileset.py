from pathlib import Path
from pathlib import Path
from typing import List, Union, Dict

import sys
import yaml


class Field:
    name: str
    description: str
    values: Dict[str, str]

    def __init__(self, name: str, definition: Union[str, dict]):
        self.name = name
        self.description = None
        self.values = None
        if isinstance(definition, str):
            self.description = definition.strip()
        elif isinstance(definition, dict):
            self.description = definition.get('description', '').strip()
            values = definition.get('values')
            if values:
                if isinstance(values, dict):
                    self.values = values
                elif isinstance(values, list):
                    self.values = {k: None for k in values}
                elif values:
                    raise ValueError(
                        f'Field {name} has unexpected type {type(values)} for values')
        elif definition:
            raise ValueError(f'Field {name} has an unexpected type {type(definition)}')


class Layer:
    @staticmethod
    def parse(layer_filename: Union[str, Path], root_dir: Path = None,
              tileset: 'Tileset' = None) -> 'Layer':
        # if layer_filename is a rooted path, the optional root_dir will be ignored
        layer_filename = Path(root_dir or '', layer_filename).resolve()
        layer_dir = layer_filename.parent
        layer = parse_file(layer_filename)

        mapping_files = [Path(layer_dir, ds['mapping_file'])
                         for ds in layer.get('datasources', [])
                         if ds['type'] == 'imposm3']

        mappings = [parse_file(f) for f in mapping_files]

        schemas = [Path(layer_dir, f).read_text('utf-8')
                   for f in layer.get('schema', [])]

        return Layer(layer_filename, layer, mapping_files, mappings, schemas, tileset)

    def __init__(self, filename: Path, definition: dict,
                 mapping_files: List[Path], mappings: List[dict],
                 schemas: List[str], tileset: 'Tileset'):
        self.filename = filename
        self.definition = definition
        self.imposm_mapping_files = mapping_files
        self.imposm_mappings = mappings
        self.schemas = schemas
        self.tileset = tileset
        self.fields = {k: Field(k, v) for k, v in definition['layer']['fields'].items()}

    # TODO: enable deprecation warning
    # @deprecated(version='3.2.0', reason='use named properties instead')
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
        layer_fields = list(self.definition['layer']['fields'].keys())
        if self.key_field:
            layer_fields.append(self.key_field)
        return layer_fields

    @property
    def id(self) -> str:
        return self.definition['layer']['id']

    @property
    def description(self) -> str:
        return self.definition['layer'].get('description', '').strip()

    @property
    def buffer_size(self) -> int:
        return self.definition['layer']['buffer_size']

    @property
    def max_size(self) -> int:
        return self.definition.get('max_size', 512)

    @property
    def srs(self) -> str:
        return self.definition['layer'].get('srs', self.tileset.default_srs)

    @property
    def geometry_field(self) -> str:
        result = self.definition['layer']['datasource'].get(
            'geometry_field', 'geometry')
        if result in self.fields:
            raise ValueError(
                f"Layer '{self.id}' must not have the implicit "
                f"'geometry' field declared in the 'fields' section of the yaml file")
        return result

    @property
    def key_field(self) -> str:
        result = self.definition['layer']['datasource'].get('key_field')
        if result and self.key_field_as_attribute:
            # If 'yes', we will need to generate a wrapper query that includes
            # osm_id column twice - once for feature_id, and once as an attribute
            raise ValueError(f"key_field_as_attribute=yes is not yet implemented")
        return result

    @property
    def key_field_as_attribute(self) -> bool:
        val = self.definition['layer']['datasource'].get('key_field_as_attribute')
        return val and val != 'no'

    @property
    def srid(self) -> str:
        return self.definition['layer']['datasource'].get('srid',
                                                          self.tileset.default_srid)

    @property
    def query(self) -> str:
        return self.definition['layer']['datasource']['query']


class Tileset:
    filename: str
    definition: dict
    layers: List[Layer]

    @staticmethod
    def parse(tileset_filename: Union[str, Path]) -> 'Tileset':
        tileset_filename = Path(tileset_filename).resolve()
        tileset = parse_file(tileset_filename)['tileset']
        layers = []
        for layer_filename in tileset['layers']:
            layers.append(Layer.parse(layer_filename, tileset_filename.parent))
        return Tileset(tileset_filename, tileset, layers)

    def __init__(self, filename, definition, layers):
        self.filename = filename
        self.definition = definition
        self.layers = layers

    # TODO: enable deprecation warning
    # @deprecated(version='3.2.0', reason='use named properties instead')
    def __getitem__(self, attr):
        if attr in self.definition:
            return self.definition[attr]
        else:
            raise KeyError

    @property
    def attribution(self) -> str:
        return self.definition['attribution']

    @property
    def bounds(self) -> list:
        return self.definition['bounds']

    @property
    def center(self) -> list:
        return self.definition['center']

    @property
    def defaults(self) -> dict:
        return self.definition['defaults']

    @property
    def default_srs(self) -> str:
        return self.defaults['srs']

    @property
    def default_srid(self) -> str:
        return self.defaults['datasource']['srid']

    @property
    def description(self) -> str:
        return self.definition.get('description', '').strip()

    @property
    def id(self) -> str:
        return self.definition['id']

    @property
    def languages(self) -> List[str]:
        return self.definition.get('languages', [])

    @property
    def layer_paths(self) -> List[Path]:
        return [l.filename for l in self.layers]

    @property
    def maxzoom(self) -> int:
        return self.definition['maxzoom']

    @property
    def minzoom(self) -> int:
        return self.definition['minzoom']

    @property
    def name(self) -> str:
        return self.definition['name']

    @property
    def pixel_scale(self) -> int:
        return self.definition['pixel_scale']

    @property
    def version(self) -> str:
        return self.definition['version']


def parse_file(file: Path) -> dict:
    with file.open() as stream:
        try:
            return yaml.full_load(stream)
        except yaml.YAMLError as e:
            print(f'Could not parse {file}')
            print(e)
            sys.exit(1)
