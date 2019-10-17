from .tileset import Tileset


def collect_sql(tileset_filename, parallel=False):
    """If parallel is True, returns a sql value that must be executed first,
        and a lists of sql values that can be ran in parallel.
        If parallel is False, returns a single sql string"""
    tileset = Tileset.parse(tileset_filename)

    definition = tileset.definition
    languages = map(lambda l: str(l), definition.get('languages', []))
    shared_sql = get_slice_language_tags(languages)

    parallel_sql = []

    for layer in tileset.layers:
        sql = layer_notice(layer['layer']['id'])
        for schema in layer.schemas:
            sql += schema
        parallel_sql.append(sql)

    if parallel:
        return shared_sql, parallel_sql
    else:
        return shared_sql + ''.join(parallel_sql)


def layer_notice(layer_name):
    return f"DO $$ BEGIN RAISE NOTICE 'Layer {layer_name}'; END$$;"


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
