from typing import Iterable, Tuple, Dict, Set, Union

from asyncpg import Connection
# noinspection PyProtectedMember
from docopt import DocoptExit

from openmaptiles.consts import PIXEL_SCALE
from openmaptiles.language import language_codes_to_names, languages_to_sql
from openmaptiles.tileset import Tileset, Layer


class MvtGenerator:
    layer_ids: Set[str]

    def __init__(self, tileset: Union[str, Tileset], layer_ids: Iterable[str] = None,
                 key_column=False, gzip: Union[int, bool] = False, use_feature_id=True):
        if isinstance(tileset, str):
            self.tileset = Tileset.parse(tileset)
        else:
            self.tileset = tileset
        self.extent = 4096
        self.pixel_width = PIXEL_SCALE
        self.pixel_height = PIXEL_SCALE
        self.key_column = key_column
        self.gzip = gzip
        self.use_feature_id = use_feature_id
        self.set_layer_ids(layer_ids)

    def set_layer_ids(self, layer_ids: Iterable[str]):
        self.layer_ids = set(layer_ids or [])

    def generate_sqltomvt_func(self, fname):
        """
        Creates a SQL function that returns a single bytea value or null
        """
        return f"""\
CREATE OR REPLACE FUNCTION {fname}(zoom integer, x integer, y integer)
RETURNS {'TABLE(mvt bytea, key text)' if self.key_column else 'bytea'} AS $$
{self.generate_query("TileBBox(zoom, x, y)", "zoom")};
$$ LANGUAGE SQL STABLE RETURNS NULL ON NULL INPUT;"""

    def generate_sqltomvt_preparer(self, fname):
        """
        Creates a SQL prepared statement that returns 0 or 1 row with a single mvt column.
        """
        return f"""\
-- Delete prepared statement if it already exists
DO $$ BEGIN
IF EXISTS (SELECT * FROM pg_prepared_statements where name = '{fname}') THEN
  DEALLOCATE {fname};
END IF;
END $$;

-- Run this statement with   EXECUTE {fname}(zoom, x, y)
PREPARE {fname}(integer, integer, integer) AS
{self.generate_sqltomvt_query()};"""

    def generate_sqltomvt_query(self):
        return self.generate_query("TileBBox($1, $2, $3)", "$1")

    def generate_sqltomvt_psql(self):
        return self.generate_query("TileBBox(:zoom, :x, :y)", ":zoom")

    def generate_sqltomvt_raw(self):
        return self.generate_query()

    def generate_query(self, bbox: str = None, zoom: str = None):
        queries = []
        found_layers = set()
        for layer_id, layer in self.get_layers():
            found_layers.add(layer_id)
            query = self.generate_layer(layer, zoom, bbox)
            queries.append(query)
        if self.layer_ids and self.layer_ids != found_layers:
            unknown = sorted(self.layer_ids - found_layers)
            raise DocoptExit(
                f"Unable to find layer [{', '.join(unknown)}]. Available layers:\n" +
                '\n'.join(f"* {v['layer']['id']}" + (
                    f"\n{v['layer']['description']}" if v['layer'].get('description')
                    else ''
                ) for v in self.tileset.layers)
            )
        if not queries:
            raise DocoptExit('Could not find any layer definitions')

        concatenate_layers = "STRING_AGG(mvtl, '')"
        # Handle when gzip is True or a number
        # Note that any bool is an int, but not reverse: isinstance(False, int) == True
        if not isinstance(self.gzip, bool) or self.gzip:
            # GZIP function is available from https://github.com/pramsey/pgsql-gzip
            if isinstance(self.gzip, bool):
                concatenate_layers = f"GZIP({concatenate_layers})"
            else:
                self.gzip = int(self.gzip)
                assert 0 <= self.gzip <= 9
                concatenate_layers = f"GZIP({concatenate_layers}, {self.gzip})"
        union_layers = "\n    UNION ALL\n  ".join(queries)
        query = f"""\
SELECT {concatenate_layers} AS mvt FROM (
  {union_layers}
) AS all_layers"""

        if self.key_column:
            query = f"SELECT mvt, md5(mvt) AS key FROM ({query}) AS mvt_data"

        return query + '\n'

    def generate_layer(self, layer_def: Layer, zoom: str, bbox: str):
        """
        Convert layer definition into a SQL statement.
        """
        layer = layer_def["layer"]
        ext = self.extent
        query = layer['datasource']['query']
        layer_fields, key_fld = layer_def.get_fields()
        if key_fld and not self.use_feature_id:
            # PostGIS < v3 did not support feature_ids
            # TODO: remove key field (osm_id) from query result to prevent
            # it being used as a regular attribute
            key_fld = None
        has_languages = '{name_languages}' in query
        if has_languages:
            languages = self.tileset.definition.get('languages', [])
            tags_field = languages_to_sql(languages)
            query = query.format(name_languages=tags_field)
        geom_fld = layer_def.geometry_field
        repl_geom_fld = f"ST_AsMVTGeom({geom_fld}, !bbox!, {ext}, " \
                        f"{layer['buffer_size']}, true) AS mvtgeometry"
        repl_query = query.replace(geom_fld, repl_geom_fld)
        if len(repl_query) - len(repl_geom_fld) + len(geom_fld) != len(query):
            raise ValueError(f"Unable to replace '{geom_fld}' in '{layer['id']}' layer")

        # Combine all layer's features into a single MVT blob representing one layer
        # only if the MVT geometry is not NULL
        # Skip the whole layer if there is nothing in it
        query = f"""\
SELECT \
COALESCE(ST_AsMVT(t, '{layer['id']}', {ext}, 'mvtgeometry'\
{f", '{key_fld}'" if key_fld else ""}), '') \
as mvtl \
FROM {repl_query}"""

        if bbox:
            query = self.substitute_sql(query, bbox, zoom)
        return query

    def substitute_sql(self, query, bbox, zoom):
        query = (query
                 .replace("!bbox!", bbox)
                 .replace("z(!scale_denominator!)", zoom)
                 .replace("!pixel_width!", str(self.pixel_width))
                 .replace("!pixel_height!", str(self.pixel_height)))
        if '!scale_denominator!' in query:
            raise ValueError(
                'MVT made an invalid assumption that "!scale_denominator!" is '
                'always used as a parameter to z() function. Either change '
                'the layer queries, or fix this code')
        return query

    async def validate_layer_fields(
        self, connection: Connection, layer_id: str, layer_def: Layer
    ) -> Dict[str, str]:
        """Validate that fields in the layer definition match the ones
        returned by the dummy (0-length) SQL query.
        Returns field names => SQL types (oid)."""
        query_field_map, languages = await self.get_sql_fields(connection, layer_def)
        query_fields = set(query_field_map.keys())
        layer_fields, key_fld = layer_def.get_fields()
        if languages:
            layer_fields += language_codes_to_names(languages)
        layer_fields = set(layer_fields)
        geom_fld = layer_def.geometry_field
        if geom_fld not in query_fields:
            raise ValueError(
                f"Layer '{layer_id}' query does not generate expected '{geom_fld}'"
                f"{' (geometry)' if geom_fld != 'geometry' else ''} field")
        query_fields.remove(geom_fld)
        if layer_fields != query_fields:
            same = layer_fields.intersection(query_fields)
            layer_fields -= same
            query_fields -= same
            error = f"Declared fields in layer '{layer_id}' do not match " \
                    f"the fields received from a query:\n"
            if layer_fields:
                error += f"  These fields were declared, but not returned by " \
                         f"the query: {', '.join(layer_fields)}"
            if query_fields:
                error += f"  These fields were returned by the query, " \
                         f"but not declared: {', '.join(query_fields)}"
            raise ValueError(error)
        return query_field_map

    async def get_sql_fields(
        self, connection: Connection, layer_def: Layer
    ) -> Tuple[Dict[str, str], Iterable[str]]:
        """Get field names => SQL types (oid) by executing a dummy query"""
        query = layer_def["layer"]['datasource']['query']
        if '{name_languages}' in query:
            languages = self.tileset.definition.get('languages', [])
            query = query.format(name_languages=languages_to_sql(languages))
        else:
            languages = False
        query = self.substitute_sql(query, "TileBBox(0, 0, 0)", "0")
        st = await connection.prepare(f"SELECT * FROM {query} WHERE false LIMIT 0")
        query_field_map = {fld.name: fld.type.oid for fld in st.get_attributes()}
        return query_field_map, languages

    def get_layers(self) -> Iterable[Tuple[str, Layer]]:
        for layer in self.tileset.layers:
            layer_id = layer["layer"]['id']
            if not self.layer_ids or layer_id in self.layer_ids:
                yield layer_id, layer
