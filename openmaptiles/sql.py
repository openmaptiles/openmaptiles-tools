import re

from .tileset import Tileset


def collect_sql(tileset_filename, parallel=False):
    """If parallel is True, returns a sql value that must be executed first,
        and a lists of sql values that can be ran in parallel.
        If parallel is False, returns a single sql string"""
    tileset = Tileset.parse(tileset_filename)

    definition = tileset.definition
    languages = map(lambda l: str(l), definition.get('languages', []))
    run_first = get_slice_language_tags(languages)
    run_last = ''  # at this point we don't have any SQL to run at the end

    parallel_sql = []
    for layer in tileset.layers:
        name = layer['layer']['id']
        schemas = '\n\n'.join((to_sql(v, layer) for v in layer.schemas))
        parallel_sql.append(f"""\
DO $$ BEGIN RAISE NOTICE 'Processing layer {name}'; END$$;

{schemas}

DO $$ BEGIN RAISE NOTICE 'Finished layer {name}'; END$$;
""")

    if parallel:
        return run_first, parallel_sql, run_last
    else:
        return run_first + '\n'.join(parallel_sql) + run_last


def get_slice_language_tags(languages):
    include_tags = list(map(lambda l: 'name:' + l, languages))
    include_tags.append('int_name')
    include_tags.append('loc_name')
    include_tags.append('name')
    include_tags.append('wikidata')
    include_tags.append('wikipedia')

    tags_sql = "'" + "', '".join(include_tags) + "'"

    return f"""\
CREATE OR REPLACE FUNCTION slice_language_tags(tags hstore)
RETURNS hstore AS $$
    SELECT delete_empty_keys(slice(tags, ARRAY[{tags_sql}]))
$$ LANGUAGE SQL IMMUTABLE;
"""


def to_sql(sql, layer):
    """Clean up SQL, and perform any needed code injections"""
    sql = sql.strip()

    # Replace "%%FIELD_MAPPING: <fieldname>%%" with fields from layer definition
    def field_map(match):
        indent = match.group(1)
        field = match.group(2)
        fields = layer.definition['layer']['fields']
        if field not in fields:
            raise ValueError(f"Field '{field}' not found in the layer definition file")
        if 'values' not in fields[field]:
            raise ValueError(
                f"Field '{field}' has no values defined in the layer definition file")
        values = fields[field]['values']
        if not isinstance(values, dict):
            raise ValueError(f"Definition for {field}/values has to be a dictionary")
        conditions = []
        for map_to, mapping in values.items():
            # mapping is a dictionary of input_fields -> (a value or a list of values)
            whens = []
            for in_fld, in_vals in mapping.items():
                if isinstance(in_vals, str):
                    in_vals = [in_vals]
                if len(in_vals) == 1:
                    expr = f"={sql_value(in_vals[0])}"
                else:
                    expr = f" IN ({', '.join((sql_value(v) for v in in_vals))})"
                whens.append(f'{sql_field(in_fld)}{expr}')
            cond = f'\n{indent}    OR '.join(whens) + \
                   (' ' if len(whens) == 1 else f'\n{indent}    ')
            conditions.append(f"WHEN {cond}THEN {sql_value(map_to)}")
        return indent + f'\n{indent}'.join(conditions)

    sql = re.sub(r'( *)%%\s*FIELD_MAPPING\s*:\s*([a-zA-Z0-9_-]+)\s*%%', field_map, sql)

    return sql


def sql_field(field):
    return f'"{field}"'


def sql_value(value):
    if "'" not in value:
        return f"'{value}'"
    return "E'" + value.replace('\\', '\\\\').replace("'", "\\'") + "'"
