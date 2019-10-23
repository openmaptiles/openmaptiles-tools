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
        schemas = '\n\n'.join((v.strip() for v in layer.schemas))
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
