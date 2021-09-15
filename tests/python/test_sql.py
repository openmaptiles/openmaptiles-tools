from dataclasses import dataclass
from pathlib import Path
from unittest import main, TestCase

from typing import List, Union, Dict

from openmaptiles.sql import collect_sql
from openmaptiles.tileset import ParsedData, Tileset


@dataclass
class Case:
    id: str
    query: str
    reqs: Union[str, List[str], Dict[str, Union[str, List[str]]]] = None


def expected_sql(case: Case):
    result = f"DO $$ BEGIN RAISE NOTICE 'Processing layer {case.id}'; END$$;\n\n"
    if isinstance(case.reqs, dict):
        for table in case.reqs.get('tables', []):
            result += f"-- Assert {table} exists\nSELECT '{table}'::regclass;\n\n"
        for func in case.reqs.get('functions', []):
            result += f"-- Assert {func} exists\nSELECT '{func}'::regprocedure;\n\n"
    result += f"""\
-- Layer {case.id} - {case.id}_s.yaml

{case.query}

DO $$ BEGIN RAISE NOTICE 'Finished layer {case.id}'; END$$;
"""
    return result


def parsed_data(layers: Union[Case, List[Case]]):
    return ParsedData(dict(
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
                        requires=[v.reqs] if isinstance(v.reqs, str) else v.reqs or []
                    ),
                    schema=[ParsedData(v.query, Path(v.id + '_s.yaml'))] if v.query else [],
                ), Path(f'./{v.id}.yaml')) for v in ([layers] if isinstance(layers, Case) else layers)
            ],
            maxzoom="test_maxzoom",
            minzoom="test_minzoom",
            name="test_name",
            pixel_scale="test_pixel_scale",
            version="test_version",
        ))), Path("./tileset.yaml"))


class SqlTestCase(TestCase):

    def _test(self, name, layers: List[Case],
              expect: Dict[str, Union[Case, List[Case]]]):
        expected_first = """\
-- This SQL code should be executed first

CREATE OR REPLACE FUNCTION slice_language_tags(tags hstore)
RETURNS hstore AS $$
    SELECT delete_empty_keys(slice(tags, ARRAY['int_name', 'loc_name', 'name', 'wikidata', 'wikipedia']))
$$ LANGUAGE SQL IMMUTABLE;
"""
        expected_last = "-- This SQL code should be executed last\n"

        ts = parsed_data(layers)

        result = {
            k: "\n".join(
                [expected_sql(vv) for vv in ([v] if isinstance(v, Case) else v)]
            ) for k, v in expect.items()}

        # Show entire diff in case assert fails
        self.maxDiff = None

        self.assertEqual(expected_first + "\n" + "\n".join(result.values()) + "\n" + expected_last,
                         collect_sql(ts, parallel=False),
                         msg=f"{name} - single file")

        self.assertEqual((expected_first, result, expected_last),
                         collect_sql(ts, parallel=True),
                         msg=f"{name} - parallel")

    def test_require(self):
        c1 = Case("c1", "SELECT 1;")
        c2 = Case("c2", "SELECT 2;")
        c3r2 = Case("c3", "SELECT 3;", reqs="c2")
        c4r12 = Case("c4", "SELECT 4;", reqs=["c1", "c2"])
        c5r3 = Case("c5", "SELECT 5;", reqs="c3")
        c6r4 = Case("c6", "SELECT 6;", reqs="c4")
        c7r2 = Case("c7", "SELECT 7;", reqs=dict(layers="c2"))
        c8r12 = Case("c8", "SELECT 8;", reqs=dict(layers=["c1", "c2"]))
        c9 = Case("c9", "SELECT 9;", reqs=dict(tables=["tbl1"]))
        c10 = Case("c10", "SELECT 10;", reqs=dict(tables=["tbl1", "tbl2"]))
        c11 = Case("c11", "SELECT 11;", reqs=dict(functions=["fnc1"]))
        c12 = Case("c12", "SELECT 12;", reqs=dict(functions=["fnc1", "fnc2"]))

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

    def _parse_reqs(self, reqs, expected_layers, expected_tables, expected_funcs):
        ts = Tileset(parsed_data(Case('my_id', 'my_query;', reqs=reqs)))
        self.assertEqual(ts.attribution, "test_attribution")
        self.assertEqual(ts.bounds, "test_bounds")
        self.assertEqual(ts.center, "test_center")
        self.assertEqual(ts.defaults, dict(srs="test_srs", datasource=dict(srid="test_datasource")))
        self.assertEqual(ts.id, "id1")
        self.assertEqual(ts.maxzoom, "test_maxzoom")
        self.assertEqual(ts.minzoom, "test_minzoom")
        self.assertEqual(ts.name, "test_name")
        self.assertEqual(ts.pixel_scale, "test_pixel_scale")
        self.assertEqual(ts.version, "test_version")

        self.assertEqual(len(ts.layers), 1)
        layer = ts.layers_by_id['my_id']
        self.assertEqual(layer.id, "my_id")
        self.assertEqual(layer.requires_layers, expected_layers)
        self.assertEqual(layer.requires_tables, expected_tables)
        self.assertEqual(layer.requires_functions, expected_funcs)

    def test_parse_reqs(self):
        self._parse_reqs(None, [], [], [])
        self._parse_reqs([], [], [], [])
        self._parse_reqs({}, [], [], [])
        self._parse_reqs(dict(tables="a"), [], ["a"], [])
        self._parse_reqs(dict(tables=["a", "b"]), [], ["a", "b"], [])
        self._parse_reqs(dict(functions="a"), [], [], ["a"])
        self._parse_reqs(dict(functions=["a", "b"]), [], [], ["a", "b"])


if __name__ == '__main__':
    main()
