from dataclasses import dataclass
import os
from pathlib import Path
from typing import List, Union, Dict, Any, Callable, Optional, NewType

import sys
import warnings
import yaml
from deprecated import deprecated

from .utils import print_err

GetEnv = NewType('GetEnv', Callable[[str, Optional[str]], Optional[str]])


def tag_fields_to_sql(fields):
    """Converts a list of fields stored in the tags hstore into a list of SQL fields:
        name:en   =>   NULLIF(tags->'name:en', '') AS name:en
    """
    return [f"NULLIF(tags->'{fld}', '') AS \"{fld}\"" for fld in fields]


def assert_int(value, name: str, min_val: Optional[int] = None, max_val: Optional[int] = None, required=False):
    if value is None:
        if required:
            raise ValueError(f'Value {name} does not exist')
        return None
    elif isinstance(value, str):
        try:
            value = int(value)
        except ValueError:
            raise ValueError(f'Unable to parse {name} value "{value}" as an integer')
    elif not isinstance(value, int):
        raise ValueError(f'The {name} value was expected to be an integer, but found {type(value).__name__} "{value}"')
    if min_val is not None and value < min_val:
        raise ValueError(f'The {name} value {value} is less than the minimum allowed {min_val}')
    if max_val is not None and value > max_val:
        raise ValueError(f'The {name} value {value} is more than the maximum allowed {max_val}')
    return value


@dataclass
class ParsedData:
    data: Union[dict, str]
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
            return f'{self.name} -- {self.description}'
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
                 tileset: 'Tileset' = None,
                 index: int = None,
                 overrides: dict = None):
        """
        :param layer_source: load layer from this source, e.g. a file
        :param tileset: parent tileset object (optional)
        :param index: layer's position index within the tileset
        :param overrides: additional override parameters for this layer
        """
        self.tileset = tileset
        self.index = index
        self.overrides = overrides if overrides is not None else {}
        self._getenv = self.tileset.getenv if self.tileset else os.getenv

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

        schemas = [
            (f.path, f.data) if isinstance(f, ParsedData)
            else (f, Path(layer_dir, f).read_text('utf-8'))
            for f in self.definition.get('schema', [])
        ]
        self.schemas = [f'-- Layer {self.id} - {p}\n\n{d}' for p, d in schemas]

        if self.definition['layer'].get('fields'):
            self.fields = [Field(k, v) for k, v in
                           self.definition['layer']['fields'].items()]
        else:
            self.fields = []

        requires = self.definition['layer'].get('requires', {})
        if not isinstance(requires, dict):
            requires = dict(layers=requires)
        else:
            requires = requires.copy()  # dict will be modified to detect unrecognized properties

        err = 'If set, "requires" parameter must be a map with optional "layers", "tables", and "functions" sub-elements. Each sub-element must be a string or a list of strings. If "requires" is a list or a string itself, it is treated as a list of layers. ' + \
              'Optionally add "helpText" sub-element string to help the user with generating missing tables and functions.'
        self.requires_layers = get_requires_prop(
            requires, 'layers',
            err + '"requires.layers" must be an ID of another layer, or a list of layer IDs.')
        self.requires_tables = get_requires_prop(
            requires, 'tables',
            err + '"requires.tables" must be the name of a PostgreSQL table or a view, or a list of tables/views')
        self.requires_functions = get_requires_prop(
            requires, 'functions',
            err + '"requires.functions" must be a PostgreSQL function name with parameters or a list of functions. Example: "sql_func(TEXT, TEXT)"')

        self.requires_helpText = None
        if requires.get('helpText'):
            self.requires_helpText = requires.get('helpText')
            requires.pop('helpText', [])

        if requires:
            # get_requires_prop will delete the key it handled. Remaining keys are errors.
            raise ValueError(f'Unrecognized sub-elements in the \"requires\" parameter: {str(list(requires.keys()))}')

        validate_properties(self, f'Layer {self.filename}')

        if any(v.name == self.geometry_field for v in self.fields):
            raise ValueError(
                f'Layer "{self.id}" must not have an implicit "{self.geometry_field}" '
                f'field declared in the "fields" section of the yaml file')
        if self.key_field and self.key_field_as_attribute:
            # If 'yes', we will need to generate a wrapper query that includes
            # osm_id column twice - once for feature_id, and once as an attribute
            raise ValueError('key_field_as_attribute=yes is not yet implemented')

        self._vars = self._assemble_vars()

    def _assemble_vars(self) -> Dict[str, str]:
        # Compute layer variables including the override logic.
        # Priority order (last wins):  layer, tileset global, tileset per layer, env vars
        result = self.definition['layer'].get('vars', {})
        if self.tileset:
            for name, value in self.tileset.overrides.get('vars', {}).items():
                if name in result:
                    result[name] = value
        for name, value in self.overrides.get('vars', {}).items():
            if name not in result:
                raise ValueError(f'Layer override variable "{name}" is not defined in the layer')
            result[name] = value
        for name in result.keys():
            result[name] = self.getenv(f'OMT_VAR_{name}', result[name])
        return result

    def getenv(self, name: str, default: str = '') -> str:
        # Allow empty env var to be the same as unset.
        value = self._getenv(name, '')
        return value if value != '' else default

    def get_fields(self) -> List[str]:
        """Get a list of field names this layer generates.
           Geometry field is not included."""
        if self.definition['layer'].get('fields'):
            layer_fields = list(self.definition['layer']['fields'].keys())
        else:
            layer_fields = []
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
        """
        Layer's buffer size is computed from `buffer_size` and `min_buffer_size` from layer and tileset files,
        as well the TILE_BUFFER_SIZE env var using this logic:

        max(
          first_found_value(
            TILE_BUFFER_SIZE env variable,
            buffer_size set in the tileset yaml file layer's section (per layer override),
            buffer_size set in the tileset yaml file at the top level (global override),
            buffer_size set in the layer yaml file,
            0),
          first_found_value(
            min_buffer_size set in the tileset yaml file layer's section (per layer override),
            min_buffer_size set in the layer yaml file,
            0)
        )

        Note that the layer yaml file must define either buffer_size or min_buffer_size or both.
        """
        # Read layer yaml file
        size = assert_int(self.definition['layer'].get('buffer_size'), 'buffer_size', min_val=0)
        min_size = assert_int(self.definition['layer'].get('min_buffer_size'), 'min_buffer_size', min_val=0)
        if size is None and min_size is None:
            raise ValueError(f'Layer "{self.id}" is missing an integer buffer_size and/or min_buffer_size')
        elif size is not None and min_size is not None:
            if size < min_size:
                raise ValueError(f'Layer "{self.id}" has buffer_size less than min_buffer_size')
        elif size is None:
            # size is not set, will use min_size as default (at the end)
            size = 0
        else:
            # size is set, min_size is not set
            min_size = 0
        # Override with tileset global values
        if self.tileset:
            val = assert_int(self.tileset.overrides.get('buffer_size'), 'buffer_size global override', min_val=0)
            if val is not None:
                size = val
        # Override with tileset per-layer values
        if self.overrides:
            val = assert_int(self.overrides.get('buffer_size'), 'buffer_size layer override', min_val=0)
            min_val = assert_int(self.overrides.get('min_buffer_size'), 'min_buffer_size layer override', min_val=0)
            if val is not None and min_val is not None and val < min_val:
                raise ValueError(f'Layer overrides for "{self.id}" have buffer_size less than min_buffer_size')
            if val is not None:
                size = val
            if min_val is not None:
                min_size = min_val
        # Override with ENV variables
        tbs = self.getenv('TILE_BUFFER_SIZE')
        val = assert_int(tbs if tbs != '' else None, 'TILE_BUFFER_SIZE env var', min_val=0)
        if val is not None:
            size = val
        # Ensure buffer is no less than the minimum
        if size < min_size:
            size = min_size
        return size

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

    def get_var(self, name: str) -> str:
        if name not in self._vars:
            raise ValueError(f'Variable {name} does not exist in layer {self.id}')
        return str(self._vars[name])

    @property
    @deprecated(version='5.4.0', reason='use requires_layers property instead')
    def requires(self) -> List[str]:
        return self.requires_layers

    def __str__(self) -> str:
        if self.tileset:
            path = self.filename.relative_to(self.tileset.filename.parent)
        else:
            path = self.filename
        return f'{self.id} ({path})'


class Tileset:
    # These fields will always be included, in addition to the ones in tile definition
    auto_language_fields = ['name_int', 'name:latin', 'name:nonlatin']

    filename: Path
    definition: dict
    layers: List[Layer]
    getenv: GetEnv

    @staticmethod
    def parse(tileset_source: Union[str, Path, ParsedData]) -> 'Tileset':
        return Tileset(tileset_source)

    def __init__(self, tileset_source: Union[str, Path, ParsedData], getenv: GetEnv = None):
        """Create a new tileset from a file (str|Path), or already parsed.
        Optionally provide environment variables (used in unit testing)."""
        self.getenv = getenv or os.getenv
        if isinstance(tileset_source, ParsedData):
            self.filename = tileset_source.path
            data = tileset_source.data
        else:
            self.filename = Path(tileset_source).resolve()
            data = parse_file(self.filename)

        self.definition = data['tileset']
        self.layers = []
        self.layers_by_id = {}

        layer_obj: Union[str, Path, ParsedData, dict]
        for index, layer_obj in enumerate(self.definition['layers']):
            if isinstance(layer_obj, dict):
                layer = Layer(layer_obj['file'], self, index, layer_obj)
            else:
                layer = Layer(layer_obj, self, index, overrides=None)
            if layer.id in self.layers_by_id:
                raise ValueError(f"Layer '{layer.id}' is defined more than once")
            self.layers.append(layer)
            self.layers_by_id[layer.id] = layer

        # Detect circular dependencies and missing layer IDs for the 'requires' field
        resolved = set()
        unresolved = self.layers_by_id.copy()
        last_count = -1
        while len(resolved) > last_count:
            last_count = len(resolved)
            for lid, layer in list(unresolved.items()):
                for req in layer.requires_layers:
                    if req not in self.layers_by_id:
                        raise ValueError(f"Unknown layer '{req}' required for "
                                         f'layer {layer.id}')
                    if req not in resolved:
                        break
                else:
                    # all requirements are already in resolved (or no reqs)
                    resolved.add(lid)
                    del unresolved[lid]
        if unresolved:
            raise ValueError('Circular dependency found in layer requirements: '
                             + ', '.join(unresolved.keys()))

        validate_properties(self, f'Tileset {self.filename}')

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
    def overrides(self) -> dict:
        return self.definition.get('overrides', {})

    @property
    def pixel_scale(self) -> int:
        return self.definition['pixel_scale']

    @property
    def version(self) -> str:
        return self.definition['version']

    def languages_as_fields(self) -> List[str]:
        """
        Get languages as a list of SQL field names,
        decorated as 'name:code', as well as the default ones.
        """
        return [f'name:{lang}'
                for lang in self.languages] + Tileset.auto_language_fields

    def languages_as_sql_fields(self) -> List[str]:
        """Get language codes as a list of SQL fields:
            en   =>   NULLIF(tags->'name:en', '') AS name:en
        """
        return tag_fields_to_sql(self.languages_as_fields())

    def __str__(self) -> str:
        return f'{self.name} ({self.filename})'


def parse_file(file: Path) -> dict:
    with file.open() as stream:
        try:
            return yaml.full_load(stream)
        except yaml.YAMLError as e:
            print_err(f'Could not parse {file}')
            print_err(e)
            sys.exit(1)


def validate_properties(obj, info):
    """Ensure that none of the object properties raise errors"""
    with warnings.catch_warnings():
        # Validation should test properties without warnings even if they are deprecated
        warnings.filterwarnings('ignore', category=DeprecationWarning)
        errors = []
        for attr in dir(obj):
            try:
                getattr(obj, attr)
            except Exception as ex:
                errors.append((attr, ex))
        if errors:
            err = f'\n{info} has invalid data:\n'
            err += '\n'.join((f'  * {n}: {repr(e)}' for n, e in errors))
            err += '\n'
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
        raise ValueError(f'Unrecognized content in file {filename} '
                         f'- expecting "tileset" or "layer" top element')


def get_requires_prop(requires: Dict[str, Union[str, List[str]]], prop: str, err: str) -> List[str]:
    """
    Extract and delete a property from a dictionary, and ensure that the property is a valid list of strings.
    """
    result = requires.pop(prop, [])
    if isinstance(result, str):
        result = [result]
    if not isinstance(result, list) or any(not isinstance(v, str) or v == '' for v in result):
        raise ValueError(err)
    return result
