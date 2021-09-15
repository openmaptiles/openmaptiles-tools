import re
from .tileset import Tileset


def zres(pixel_scale, zoom):
    # See https://github.com/openmaptiles/postgis-vt-util/blob/master/src/ZRes.sql
    return 40075016.6855785 / ((1.0 * float(pixel_scale)) * 2 ** float(zoom))


def call_zres(pixel_scale, match):
    # See https://github.com/openmaptiles/postgis-vt-util/blob/master/src/ZRes.sql
    return str(zres(pixel_scale, match.group(0)[4:6]))


def create_imposm3_mapping(tileset_filename):
    tileset = Tileset.parse(tileset_filename)
    definition = tileset.definition

    pixel_scale = tileset.definition['pixel_scale']

    languages = map(lambda l: str(l), definition.get('languages', []))
    include_tags = list(map(lambda l: 'name:' + l, languages))
    include_tags.append('int_name')
    include_tags.append('loc_name')
    include_tags.append('name')
    include_tags.append('wikidata')
    include_tags.append('wikipedia')

    generalized_tables = {}
    tables = {}

    for layer in tileset.layers:
        for mapping in layer.imposm_mappings:
            for table_name, definition in mapping.get('generalized_tables', {}).items():
                if 'tolerance' in definition:
                    try:  # Test if numeric
                        float(definition['tolerance'])
                    except ValueError:
                        if re.match(r'^ZRES\d{1,2}$', definition['tolerance']):
                            zoom = definition['tolerance'][4:6]
                            # Convert to distance
                            definition['tolerance'] = zres(pixel_scale, zoom)
                        else:
                            raise SyntaxError(
                                f"Unrecognized tolerance '{definition['tolerance']}'")
                if 'sql_filter' in definition:
                    definition['sql_filter'] = re.sub(
                        r'ZRES\d{1,2}',
                        lambda match: call_zres(pixel_scale, match),
                        definition['sql_filter'])
                generalized_tables[table_name] = definition
            for table_name, definition in mapping.get('tables', {}).items():
                # Remove all OpenMapTiles custom keys to avoid confusing Imposm
                definition.pop('_resolve_wikidata', None)
                tables[table_name] = definition
            for tags_key, tags_val in mapping.get('tags', {}).items():
                if tags_key == 'include':
                    if not isinstance(tags_val, list) or any(
                        (v for v in tags_val if not v or not isinstance(v, str))
                    ):
                        raise ValueError(f"Tileset {tileset.name} mapping's "
                                         f'tags/include must be a list of strings')
                    include_tags += tags_val
                else:
                    raise ValueError(f'Tileset {tileset.name} mapping tags '
                                     f"uses an unsupported key '{tags_key}'")

    return {
        'tags': dict(include=list(sorted(set(include_tags)))),
        'generalized_tables': generalized_tables,
        'tables': tables,
    }
