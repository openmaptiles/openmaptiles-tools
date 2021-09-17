import re
from typing import Union, Dict, Tuple

from sys import stderr

from openmaptiles.tileset import Tileset, Layer


def collect_sql(tileset_filename, parallel=False, nodata=False
                ) -> Union[str, Tuple[str, Dict[str, str], str]]:
    """If parallel is True, returns a sql value that must be executed first, last,
        and a dict of names -> sql code that can be ran in parallel.
        If parallel is False, returns a single sql string.
        nodata=True replaces all '/* DELAY_MATERIALIZED_VIEW_CREATION */'
        with the "WITH NO DATA" SQL."""
    tileset = Tileset(tileset_filename)

    run_first = '-- This SQL code should be executed first\n\n' + \
                get_slice_language_tags(tileset)
    # at this point we don't have any SQL to run at the end
    run_last = '-- This SQL code should be executed last\n'

    # resolved is a map of layer ID to some ID in results.
    # the ID in results could be the same as layer ID, or it could be a tuple of IDs
    resolved = {}
    # results is an ID -> SQL content map
    results = {}
    unresolved = tileset.layers_by_id.copy()
    last_count = -1
    # safety to prevent infinite loop, even though it is also checked in tileset
    while len(resolved) > last_count:
        last_count = len(resolved)
        for lid, layer in list(unresolved.items()):
            if all((v in resolved for v in layer.requires_layers)):
                # All requirements have been resolved.
                resolved[lid] = lid
                results[lid] = layer_to_sql(layer, nodata)
                del unresolved[lid]

                if layer.requires_layers:
                    # If there are more than one requirement, merge them first,
                    # e.g. if there are layers A, B, and C; and C requires A & B,
                    # first concatenate A and B, and then append C to them.
                    # Make sure the same code is not merged multiple times
                    mix = list(layer.requires_layers) + [lid]
                    lid1 = mix[0]
                    for idx in range(1, len(mix)):
                        lid2 = mix[idx]
                        res_id1 = resolved[lid1]
                        res_id2 = resolved[lid2]
                        if res_id1 == res_id2:
                            continue
                        merged_id = res_id1 + '__' + res_id2
                        if merged_id in results:
                            raise ValueError(f'Naming collision - {merged_id} exists')
                        # NOTE: merging will move entity to the end of the list
                        results[merged_id] = results[res_id1] + '\n' + results[res_id2]
                        del results[res_id1]
                        del results[res_id2]
                        # Update resolved IDs to point to the merged result
                        for k, v in resolved.items():
                            if v == res_id1 or v == res_id2:
                                resolved[k] = merged_id
    if unresolved:
        raise ValueError('Circular dependency found in layer requirements: '
                         + ', '.join(unresolved.keys()))

    if not parallel:
        sql = '\n'.join(results.values())
        return f'{run_first}\n{sql}\n{run_last}'
    else:
        return run_first, results, run_last


def layer_to_sql(layer: Layer, nodata: bool):
    sql = f"DO $$ BEGIN RAISE NOTICE 'Processing layer {layer.id}'; END$$;\n\n"
    for table in layer.requires_tables:
        sql += f"-- Assert {table} exists\nSELECT '{table}'::regclass;\n\n"
    for func in layer.requires_functions:
        sql += f"-- Assert {func} exists\nSELECT '{func}'::regprocedure;\n\n"
    for schema in layer.schemas:
        sql += to_sql(schema, layer, nodata) + '\n\n'
    sql += f"DO $$ BEGIN RAISE NOTICE 'Finished layer {layer.id}'; END$$;\n"

    return sql


def get_slice_language_tags(tileset):
    include_tags = list(map(lambda l: 'name:' + l, tileset.languages))
    include_tags.append('int_name')
    include_tags.append('loc_name')
    include_tags.append('name')
    include_tags.append('wikidata')
    include_tags.append('wikipedia')

    r = re.compile(r'(?:^|[_:])name(?:[_:]|$)')
    for layer in tileset.layers:
        for mapping in layer.imposm_mappings:
            for tags_key, tags_val in mapping.get('tags', {}).items():
                if tags_key == 'include':
                    if not isinstance(tags_val, list) or any(
                            (v for v in tags_val if not v or not isinstance(v, str))
                    ):
                        raise ValueError(f"Tileset {tileset.name} mapping's "
                                         f'tags/include must be a list of strings')
                    include_tags += (v for v in tags_val if r.search(v) and v not in include_tags)
                else:
                    raise ValueError(f'Tileset {tileset.name} mapping tags '
                                     f"uses an unsupported key '{tags_key}'")

    tags_sql = "'" + "', '".join(include_tags) + "'"

    return f"""\
CREATE OR REPLACE FUNCTION slice_language_tags(tags hstore)
RETURNS hstore AS $$
    SELECT delete_empty_keys(slice(tags, ARRAY[{tags_sql}]))
$$ LANGUAGE SQL IMMUTABLE;
"""


class FieldExpander:
    def __init__(self, field: str, layer: Layer, indent: str):
        field = [v for v in layer.fields if v.name == field]
        if len(field) != 1:
            raise ValueError(f'Field {field} was not found in layer {layer.id}')
        if not field[0].values:
            raise ValueError(f"Field '{field[0].name}' in layer {layer.id} "
                             f'has no defined values')
        self.field = field[0]
        self.layer = layer
        self.indent = indent

    def parse(self):
        conditions = []
        ignored = []
        for map_to, mapping in self.field.values.items():
            # mapping is a dictionary of input_fields -> (a value or a list of values)
            # If it is not a dictionary, skip it
            if not isinstance(mapping, dict) and not isinstance(mapping, list):
                ignored.append(map_to)
                continue
            expr = self.to_expression(map_to, mapping)
            if expr:
                conditions.append(expr)
            else:
                ignored.append(map_to)
        if ignored and not stderr.isatty():
            print(f"-- Assuming manual SQL handling of field '{self.field.name}' "
                  f"values [{','.join(ignored)}] in layer {self.layer.id}",
                  file=stderr)
        return self.indent + f'\n{self.indent}'.join(conditions)

    def to_expression(self, map_to, mapping: Union[dict, list], op='OR', top=True):
        if isinstance(mapping, list):
            expressions = [self.to_expression(map_to, v, top=False) for v in mapping]
        elif not isinstance(mapping, dict):
            raise ValueError(f'Definition for {self.field.name}/values/{map_to} '
                             f'in layer {self.layer.id} must be a list or a dictionary')
        elif list(mapping.keys()) == ['__AND__']:
            return self.to_expression(map_to, mapping['__AND__'], 'AND', top)
        elif list(mapping.keys()) == ['__OR__']:
            return self.to_expression(map_to, mapping['__OR__'], 'OR', top)
        else:
            if '__AND__' in mapping or '__OR__' in mapping:
                raise ValueError(
                    f'Definition for {self.field.name}/values/{map_to} in layer '
                    f'{self.layer.id} mixes __AND__ or __OR__ with values')
            expressions = []
            for in_fld, in_vals in mapping.items():
                in_fld = self.sql_field(in_fld)
                if isinstance(in_vals, str):
                    in_vals = [in_vals]
                wildcards = [self.sql_value(v) for v in in_vals if '%' in v]
                in_vals = [self.sql_value(v) for v in in_vals if '%' not in v]
                conditions = [f'{in_fld} LIKE {w}' for w in wildcards]
                if in_vals:
                    if len(in_vals) == 1:
                        conditions.insert(0, f'{in_fld} = {in_vals[0]}')
                    else:
                        conditions.insert(0, f"{in_fld} IN ({', '.join(in_vals)})")
                if op == 'OR':
                    expressions.extend(conditions)
                else:
                    expr = ' OR '.join(conditions)
                    expressions.append(f'({expr})' if len(conditions) > 1 else expr)
        if top:
            if not expressions:
                return False
            expr = f'\n{self.indent}    {op} '.join(expressions) + \
                   (' ' if len(expressions) == 1 else f'\n{self.indent}    ')
            return f'WHEN {expr}THEN {self.sql_value(map_to)}'
        elif not expressions:
            raise ValueError(f'Invalid subexpression {self.field.name}/values/{map_to} '
                             f'in layer {self.layer.id} - empty sub-conditions')
        else:
            expr = f' {op} '.join(expressions)
            return f'({expr})' if len(expressions) > 1 else expr

    @staticmethod
    def sql_field(field):
        if not re.match(r'^[a-zA-Z][_a-zA-Z0-9]*$', field):
            raise ValueError(f'Unexpected symbols in the field "{field}"')
        return f'"{field}"'

    @staticmethod
    def sql_value(value):
        if "'" not in value:
            return f"'{value}'"
        return "E'" + value.replace('\\', '\\\\').replace("'", "\\'") + "'"


def to_sql(sql: str, layer: Layer, nodata: bool):
    """Clean up SQL, and perform any needed code injections"""
    sql = sql.strip()

    # Replace '%%FIELD_MAPPING: <field_name>%%' with fields from layer definition
    def field_map(match):
        return FieldExpander(match.group(2), layer, match.group(1)).parse()

    # replace FIELD_MAPPING:<field_name> param with the generated SQL CASE statement
    sql = re.sub(r'( *)%%\s*FIELD_MAPPING\s*:\s*([a-zA-Z0-9_-]+)\s*%%', field_map, sql)

    # inject 'WITH NO DATA' for the materialized views
    if nodata:
        sql = re.sub(
            r'/\*\s*DELAY_MATERIALIZED_VIEW_CREATION\s*\*/', ' WITH NO DATA ', sql)

    return sql
