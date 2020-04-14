from dataclasses import dataclass
from pathlib import Path
from typing import List, Union, Dict, Any, Callable

import json
import sys
import yaml
from deprecated import deprecated


def tag_fields_to_sql(fields):
    """Converts a list of fields stored in the tags hstore into a list of SQL fields:
        name:en   =>   NULLIF(tags->'name:en', '') AS name:en
    """
    return [f"NULLIF(tags->'{fld}', '') AS \"{fld}\"" for fld in fields]


@dataclass
class ParsedData:
    data: dict
    path: Path


class Field:
    name: str
    description: str
    values: Dict[str, Any]

    def __init__(self, name: str, definition: Union[str, dict]):
        self.name = name.strip()
        self.description = ''
        self.values = {}
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

    def __str__(self):
        if self.description:
            return f"{self.name} -- {self.description}"
        else:
            return self.name


class Layer:
    filename: Path
    definition: dict
    imposm_mapping_files: List[Path]
    imposm_mappings: List[dict]
    schemas: List[str]
    fields: List[Field]

    @staticmethod
    def parse(layer_source: Union[str, Path, ParsedData]) -> 'Layer':
        return Layer(layer_source)

    def __init__(self,
                 layer_source: Union[str, Path, ParsedData],
                 tileset: 'Tileset' = None):
        self.tileset = tileset

        if isinstance(layer_source, ParsedData):
            self.filename = layer_source.path
            self.definition = layer_source.data
        else:
            # if layer_source is a rooted path, the optional root_path will be ignored
            root_path = tileset.filename.parent if tileset else ''
            self.filename = Path(root_path, layer_source).resolve()
            self.definition = parse_file(self.filename)

        layer_dir = self.filename.parent

        self.imposm_mapping_files = [Path(layer_dir, ds['mapping_file'])
                                     for ds in self.definition.get('datasources', [])
                                     if ds['type'] == 'imposm3']

        self.imposm_mappings = [parse_file(f) for f in self.imposm_mapping_files]

        self.schemas = [Path(layer_dir, f).read_text('utf-8')
                        for f in self.definition.get('schema', [])]

        self.fields = [Field(k, v) for k, v in
                       self.definition['layer']['fields'].items()]

        validate_properties(self, f"Layer {self.filename}")

        if any(v.name == self.geometry_field for v in self.fields):
            raise ValueError(
                f"Layer '{self.id}' must not have an implicit '{self.geometry_field}' "
                f"field declared in the 'fields' section of the yaml file")
        if self.key_field and self.key_field_as_attribute:
            # If 'yes', we will need to generate a wrapper query that includes
            # osm_id column twice - once for feature_id, and once as an attribute
            raise ValueError(f"key_field_as_attribute=yes is not yet implemented")

    @deprecated(version='3.2.0', reason='use named properties instead')
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
        """Get a list of field names this layer generates.
           Geometry field is not included."""
        layer_fields = list(self.definition['layer']['fields'].keys())
        if self.key_field:
            layer_fields.append(self.key_field)
        if self.tileset and self.has_localized_names:
            layer_fields += self.tileset.languages_as_fields()
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
        res = self.definition['layer'].get(
            'srs',
            self.tileset.default_srs if self.tileset
            else '+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 '
                 '+x_0=0.0 +y_0=0.0 +k=1.0 +units=m +nadgrids=@null '
                 '+wktext +no_defs +over')
        return res

    @property
    def srid(self) -> str:
        res = self.definition['layer']['datasource'].get(
            'srid', self.tileset.default_srid if self.tileset else '900913')
        return res

    @property
    def geometry_field(self) -> str:
        return self.definition['layer']['datasource'].get('geometry_field', 'geometry')

    @property
    def key_field(self) -> Union[str, None]:
        return self.definition['layer']['datasource'].get('key_field')

    @property
    def key_field_as_attribute(self) -> bool:
        val = self.definition['layer']['datasource'].get('key_field_as_attribute')
        return bool(val and val != 'no')

    @property
    def raw_query(self) -> str:
        """Query string as defined in the layer file"""
        return self.definition['layer']['datasource']['query']

    @property
    def has_localized_names(self) -> bool:
        return '{name_languages}' in self.raw_query

    @property
    def query(self) -> str:
        """Query string with resolved localized names.
        If parent tileset is missing, only uses automatic fields"""
        if self.tileset:
            fields = self.tileset.languages_as_sql_fields()
        else:
            fields = tag_fields_to_sql(Tileset.auto_language_fields)
        return self.raw_query.format(name_languages=(', '.join(fields)))

    def __str__(self) -> str:
        if self.tileset:
            path = self.filename.relative_to(self.tileset.filename.parent)
        else:
            path = self.filename
        return f"{self.id} ({path})"


class Tileset:
    # These fields will always be included, in addition to the ones in tile definition
    auto_language_fields = ['name_int', 'name:latin', 'name:nonlatin']

    filename: Path
    definition: dict
    layers: List[Layer]

    @staticmethod
    def parse(tileset_source: Union[str, Path, ParsedData]) -> 'Tileset':
        return Tileset(tileset_source)

    def __init__(self, tileset_source: Union[str, Path, ParsedData]):
        if isinstance(tileset_source, ParsedData):
            self.filename = tileset_source.path
            self.definition = tileset_source.data
        else:
            self.filename = Path(tileset_source).resolve()
            self.definition = parse_file(self.filename)

        self.definition = self.definition['tileset']
        self.layers = []
        for layer_filename in self.definition['layers']:
            self.layers.append(Layer(layer_filename, self))
        validate_properties(self, f"Tileset {self.filename}")

    @deprecated(version='3.2.0', reason='use named properties instead')
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
        return [v.filename for v in self.layers]

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

    def languages_as_fields(self) -> List[str]:
        """
        Get languages as a list of SQL field names,
        decorated as "name:code", as well as the default ones.
        """
        return [f"name:{lang}"
                for lang in self.languages] + Tileset.auto_language_fields

    def languages_as_sql_fields(self) -> List[str]:
        """Get language codes as a list of SQL fields:
            en   =>   NULLIF(tags->'name:en', '') AS name:en
        """
        return tag_fields_to_sql(self.languages_as_fields())

    def __str__(self) -> str:
        return f"{self.name} ({self.filename})"


def parse_file(file: Path) -> dict:
    with file.open() as stream:
        try:
            return yaml.full_load(stream)
        except yaml.YAMLError as e:
            print(f'Could not parse {file}')
            print(e)
            sys.exit(1)


def validate_properties(obj, info):
    """Ensure that none of the object properties raise errors"""
    errors = []
    for attr in dir(obj):
        try:
            getattr(obj, attr)
        except Exception as ex:
            errors.append((attr, ex))
    if errors:
        err = f"\n{info} has invalid data:\n"
        err += "\n".join((f"  * {n}: {repr(e)}" for n, e in errors))
        err += "\n"
        raise ValueError(err)


def process_layers(filename: Path, processor: Callable[[Layer, bool], None]):
    """
    Open a tileset or a layer yaml file, and execute callback for each layer.
    Second parameter indicates if this is part of a tileset or not."""
    parsed = ParsedData(parse_file(filename), filename)
    if 'tileset' in parsed.data:
        for layer in Tileset.parse(parsed).layers:
            processor(layer, True)
    elif 'layer' in parsed.data:
        processor(Layer.parse(parsed), False)
    else:
        raise ValueError(f"Unrecognized content in file {filename} "
                         f"- expecting 'tileset' or 'layer' top element")
