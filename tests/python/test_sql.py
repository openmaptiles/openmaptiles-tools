from dataclasses import dataclass
from pathlib import Path
from unittest import main, TestCase

from typing import List, Union, Dict

from openmaptiles.sql import collect_sql
from openmaptiles.tileset import ParsedData


@dataclass
class Case:
    id: str
    query: str
    reqs: Union[str, List[str]] = None
    schema = None

    def __post_init__(self):
        if self.reqs:
            self.reqs = [self.reqs] if isinstance(self.reqs, str) else self.reqs
        else:
            self.reqs = []

        if self.query:
            self.schema = [ParsedData(self.query, Path(self.id + '_s.yaml'))]
        else:
            self.schema = []


def query(case: Case):
    text = f"""\
-- Layer {case.id} - {case.id}_s.yaml

{case.query}""" if case.query else ""

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
                            requires=v.reqs
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
        c3r2 = Case("c3", "SELECT 3;", reqs="c2")
        c4r12 = Case("c4", "SELECT 4;", reqs=["c1", "c2"])
        c5r3 = Case("c5", "SELECT 5;", reqs="c3")
        c6r4 = Case("c6", "SELECT 6;", reqs="c4")

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


if __name__ == '__main__':
    main()
