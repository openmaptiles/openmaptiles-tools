from dataclasses import dataclass
from pathlib import Path
from unittest import main, TestCase

from typing import List, Union, Dict

from openmaptiles.sql import collect_sql
from openmaptiles.tileset import ParsedData, get_requires_prop


@dataclass
class Case:
    id: str
    query: str
    requires: Union[str, List[str], dict] = None
    schema = None
    requires_layers = None
    requires_tables = None
    requires_functions = None

    def __post_init__(self):
        if self.requires:
            requires = self.requires
            if not isinstance(requires, dict):
                requires = dict(layers = requires)
            else:
                requires = requires.copy()  # dict will be modified to detect unrecognized properties

            err = "If set, 'requires' parameter must be a map with optional 'layers', 'tables', and 'functions' sub-elements. Each sub-element must be a string or a list of strings. If 'requires' is a list or a string itself, it is treated as a list of layers. "

            self.requires_layers = get_requires_prop(requires, 'layers', err + "'requires.layers' must be an ID of another layer, or a list of layer IDs.")
            self.requires_tables = get_requires_prop(requires, 'tables', err + "'requires.tables' must be the name of a PostgreSQL table or a view, or a list of tables/views")
            self.requires_functions = get_requires_prop(requires, 'functions', err + "'requires.functions' must be a PostgreSQL function name with parameters or a list of functions. Example: 'myfunc(TEXT, TEXT)' ")

            if requires:
                # get_requires_prop will delete the key it handled. Remaining keys are errors.
                raise ValueError("Unrecognized sub-elements in the 'requires' parameter:" + str(list(requires.keys())))

        else:
            self.requires = []

        if self.query:
            self.schema = [ParsedData(self.query, Path(self.id + '_s.yaml'))]
        else:
            self.schema = []


def query(case: Case):
    if case.query:
        text = ""
        if case.requires_tables:
            for table in case.requires_tables:
                text += f"-- Assert {table} exists\nSELECT '{table}'::regclass;\n\n"

        if case.requires_functions:
            for func in case.requires_functions:
                text += f"-- Assert {func} exists\nSELECT '{func}'::regprocedure;\n\n"
        text += f"""\
-- Layer {case.id} - {case.id}_s.yaml

{case.query}"""
    else:
        text = ""
    return f"""\
DO $$ BEGIN RAISE NOTICE 'Processing layer {case.id}'; END$$;

{text}

DO $$ BEGIN RAISE NOTICE 'Finished layer {case.id}'; END$$;
"""


class SqlTestCase(TestCase):

    def _test(self, name, layers: List[Case],
              expect: Dict[str, Union[Case, List[Case]]]):
        first = """\
-- This SQL code should be executed first

CREATE OR REPLACE FUNCTION slice_language_tags(tags hstore)
RETURNS hstore AS $$
    SELECT delete_empty_keys(slice(tags, ARRAY['int_name', 'loc_name', 'name', 'wikidata', 'wikipedia']))
$$ LANGUAGE SQL IMMUTABLE;
"""

        last = """\
-- This SQL code should be executed last
"""

        ts = ParsedData(dict(
            tileset=(dict(
                attribution="test_attribution",
                bounds="test_bounds",
                center="test_center",
                defaults=dict(srs="test_srs", datasource=dict(srid="test_datasource")),
                id="id1",
                layers=[
                    ParsedData(dict(
                        layer=dict(
                            buffer_size="test_buffer_size",
                            datasource=dict(query="test_query"),
                            id=v.id,
                            fields={},
                            requires=v.requires
                        ),
                        schema=v.schema,
                    ), Path(f'./{v.id}.yaml')) for v in layers
                ],
                maxzoom="test_maxzoom",
                minzoom="test_minzoom",
                name="test_name",
                pixel_scale="test_pixel_scale",
                version="test_version",
            ))), Path("./tileset.yaml"))

        result = {
            k: "\n".join(
                [query(vv) for vv in ([v] if isinstance(v, Case) else v)]
            ) for k, v in expect.items()}

        self.assertEqual(first + "\n" + "\n".join(result.values()) + "\n" + last,
                         collect_sql(ts, parallel=False),
                         msg=f"{name} - single file")

        self.assertEqual((first, result, last),
                         collect_sql(ts, parallel=True),
                         msg=f"{name} - parallel")

    def test_require(self):
        c1 = Case("c1", "SELECT 1;")
        c2 = Case("c2", "SELECT 2;")
        c3r2 = Case("c3", "SELECT 3;", requires="c2")
        c4r12 = Case("c4", "SELECT 4;", requires=["c1", "c2"])
        c5r3 = Case("c5", "SELECT 5;", requires="c3")
        c6r4 = Case("c6", "SELECT 6;", requires="c4")
        c7r2 = Case("c7", "SELECT 7;", requires=dict(layers="c2"))
        c8r12 = Case("c8", "SELECT 8;", requires=dict(layers=["c1","c2"]))
        c9 = Case("c9", "SELECT 9;", requires=dict(tables="tbl1"))
        c10 = Case("c10", "SELECT 10;", requires=dict(tables=["tbl1","tbl2"]))
        c11 = Case("c11", "SELECT 11;", requires=dict(functions="fnc1"))
        c12 = Case("c12", "SELECT 12;", requires=dict(functions=["fnc1","fnc2"]))

        self._test("a01", [], {})
        self._test("a02", [c1], dict(c1=c1))
        self._test("a03", [c1, c2], dict(c1=c1, c2=c2))
        self._test("a04", [c1, c2], dict(c1=c1, c2=c2))
        self._test("a05", [c2, c3r2], dict(c2__c3=[c2, c3r2]))
        self._test("a06", [c3r2, c2], dict(c2__c3=[c2, c3r2]))
        self._test("a07", [c1, c3r2, c2], dict(c1=c1, c2__c3=[c2, c3r2]))
        self._test("a08", [c1, c2, c4r12], dict(c1__c2__c4=[c1, c2, c4r12]))
        self._test("a09", [c2, c3r2, c5r3], dict(c2__c3__c5=[c2, c3r2, c5r3]))
        self._test("a10", [c5r3, c3r2, c2], dict(c2__c3__c5=[c2, c3r2, c5r3]))
        self._test("a11", [c1, c2, c4r12, c6r4],
                   dict(c1__c2__c4__c6=[c1, c2, c4r12, c6r4]))
        self._test("a12", [c4r12, c3r2, c1, c2],
                   dict(c1__c2__c4__c3=[c1, c2, c4r12, c3r2]))

        self._test("a13", [c2, c7r2], dict(c2__c7=[c2, c7r2]))
        self._test("a14", [c1, c2, c8r12], dict(c1__c2__c8=[c1, c2, c8r12]))
        self._test("a15", [c9], dict(c9=[c9]))
        self._test("a16", [c10], dict(c10=[c10]))
        self._test("a17", [c11], dict(c11=[c11]))
        self._test("a18", [c12], dict(c12=[c12]))

if __name__ == '__main__':
    main()
