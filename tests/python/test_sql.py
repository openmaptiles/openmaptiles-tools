import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import List, Union, Dict, Optional
from unittest import main, TestCase

from openmaptiles.sql import collect_sql, sql_assert_table, sql_assert_func
from openmaptiles.tileset import ParsedData, Tileset


@dataclass
class Case:
    id: str
    query: str
    reqs: Union[str, List[str], Dict[str, Union[str, List[str]]]] = None


def expected_sql(case: Case):
    result = f"DO $$ BEGIN RAISE NOTICE 'Processing layer {case.id}'; END$$;\n\n"
    if isinstance(case.reqs, dict):
        # Use helper functions for SQL generation. Actual SQL is tested by integration tests
        for table in case.reqs.get('tables', []):
            result += sql_assert_table(table, case.reqs.get('helpText'), case.id)
        for func in case.reqs.get('functions', []):
            result += sql_assert_func(func, case.reqs.get('helpText'), case.id)

    result += f"""\
-- Layer {case.id} - {case.id}_s.yaml

{case.query}

DO $$ BEGIN RAISE NOTICE 'Finished layer {case.id}'; END$$;
"""
    return result


def parsed_data(layers: Union[Case, List[Case]]):
    return ParsedData(dict(
        tileset=(dict(
            attribution='test_attribution',
            bounds='test_bounds',
            center='test_center',
            defaults=dict(srs='test_srs', datasource=dict(srid='test_datasource')),
            id='id1',
            layers=[
                dict(file=ParsedData(dict(
                    layer=dict(
                        buffer_size='10',
                        datasource=dict(query='test_query'),
                        id=v.id,
                        fields={},
                        requires=[v.reqs] if isinstance(v.reqs, str) else v.reqs or []
                    ),
                    schema=[ParsedData(v.query, Path(v.id + '_s.yaml'))] if v.query else [],
                ), Path(f'./{v.id}.yaml'))) for v in ([layers] if isinstance(layers, Case) else layers)
            ],
            maxzoom='test_maxzoom',
            minzoom='test_minzoom',
            name='test_name',
            pixel_scale='test_pixel_scale',
            version='test_version',
        ))), Path('./tileset.yaml'))


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
        expected_last = '-- This SQL code should be executed last\n'

        ts = parsed_data(layers)

        result = {
            k: '\n'.join(
                [expected_sql(vv) for vv in ([v] if isinstance(v, Case) else v)]
            ) for k, v in expect.items()}

        # Show entire diff in case assert fails
        self.maxDiff = None

        self.assertEqual(expected_first + '\n' + '\n'.join(result.values()) + '\n' + expected_last,
                         collect_sql(ts, parallel=False),
                         msg=f'{name} - single file')

        self.assertEqual((expected_first, result, expected_last),
                         collect_sql(ts, parallel=True),
                         msg=f'{name} - parallel')

    def test_require(self):
        c1 = Case('c1', 'SELECT 1;')
        c2 = Case('c2', 'SELECT 2;')
        c3r2 = Case('c3', 'SELECT 3;', reqs='c2')
        c4r12 = Case('c4', 'SELECT 4;', reqs=['c1', 'c2'])
        c5r3 = Case('c5', 'SELECT 5;', reqs='c3')
        c6r4 = Case('c6', 'SELECT 6;', reqs='c4')
        c7r2 = Case('c7', 'SELECT 7;', reqs=dict(layers='c2'))
        c8r12 = Case('c8', 'SELECT 8;', reqs=dict(layers=['c1', 'c2']))
        c9 = Case('c9', 'SELECT 9;', reqs=dict(tables=['tbl1']))
        c10 = Case('c10', 'SELECT 10;', reqs=dict(tables=['tbl1', 'tbl2']))
        c11 = Case('c11', 'SELECT 11;', reqs=dict(functions=['fnc1']))
        c12 = Case('c12', 'SELECT 12;', reqs=dict(functions=['fnc1', 'fnc2']))
        c13 = Case('c13', 'SELECT 13;', reqs=dict(functions=['fnc1', 'fnc2'],
                                                  helpText="Custom 'ERROR MESSAGE' for missing function - single quote"))
        c14 = Case('c14', 'SELECT 14;',
                   reqs=dict(tables=['tbl1'], helpText='Custom "ERROR MESSAGE" for missing table - double quote'))

        self._test('a18', [c12], dict(c12=[c12]))
        self._test('a01', [], {})
        self._test('a02', [c1], dict(c1=c1))
        self._test('a03', [c1, c2], dict(c1=c1, c2=c2))
        self._test('a04', [c1, c2], dict(c1=c1, c2=c2))
        self._test('a05', [c2, c3r2], dict(c2__c3=[c2, c3r2]))
        self._test('a06', [c3r2, c2], dict(c2__c3=[c2, c3r2]))
        self._test('a07', [c1, c3r2, c2], dict(c1=c1, c2__c3=[c2, c3r2]))
        self._test('a08', [c1, c2, c4r12], dict(c1__c2__c4=[c1, c2, c4r12]))
        self._test('a09', [c2, c3r2, c5r3], dict(c2__c3__c5=[c2, c3r2, c5r3]))
        self._test('a10', [c5r3, c3r2, c2], dict(c2__c3__c5=[c2, c3r2, c5r3]))
        self._test('a11', [c1, c2, c4r12, c6r4],
                   dict(c1__c2__c4__c6=[c1, c2, c4r12, c6r4]))
        self._test('a12', [c4r12, c3r2, c1, c2],
                   dict(c1__c2__c4__c3=[c1, c2, c4r12, c3r2]))

        self._test('a13', [c2, c7r2], dict(c2__c7=[c2, c7r2]))
        self._test('a14', [c1, c2, c8r12], dict(c1__c2__c8=[c1, c2, c8r12]))
        self._test('a15', [c9], dict(c9=[c9]))
        self._test('a16', [c10], dict(c10=[c10]))
        self._test('a17', [c11], dict(c11=[c11]))
        self._test('a18', [c12], dict(c12=[c12]))
        self._test('a19', [c13], dict(c13=[c13]))
        self._test('a20', [c14], dict(c14=[c14]))

    def _ts_parse(self, reqs, expected_layers, expected_tables, expected_funcs, extra_cases=None):
        cases = [] if not extra_cases else list(extra_cases)
        cases.append(Case('my_id', 'my_query;', reqs=reqs))
        ts = Tileset(parsed_data(cases))
        self.assertEqual(ts.attribution, 'test_attribution')
        self.assertEqual(ts.bounds, 'test_bounds')
        self.assertEqual(ts.center, 'test_center')
        self.assertEqual(ts.defaults, dict(srs='test_srs', datasource=dict(srid='test_datasource')))
        self.assertEqual(ts.id, 'id1')
        self.assertEqual(ts.maxzoom, 'test_maxzoom')
        self.assertEqual(ts.minzoom, 'test_minzoom')
        self.assertEqual(ts.name, 'test_name')
        self.assertEqual(ts.pixel_scale, 'test_pixel_scale')
        self.assertEqual(ts.version, 'test_version')

        self.assertEqual(len(ts.layers), len(cases))
        layer = ts.layers_by_id['my_id']
        self.assertEqual(layer.id, 'my_id')
        self.assertEqual(layer.requires_layers, expected_layers)
        self.assertEqual(layer.requires_tables, expected_tables)
        self.assertEqual(layer.requires_functions, expected_funcs)
        self.assertEqual(layer.buffer_size, 10)

        # This test can be deleted once we remove the deprecated property in some future version
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=DeprecationWarning)
            self.assertEqual(layer.requires, expected_layers)

    def test_ts_parse(self):
        extra = [Case('c1', 'SELECT 1;')]

        self._ts_parse(None, [], [], [])
        self._ts_parse([], [], [], [])
        self._ts_parse({}, [], [], [])
        self._ts_parse('c1', ['c1'], [], [], extra)
        self._ts_parse(['c1'], ['c1'], [], [], extra)
        self._ts_parse(dict(layers='c1'), ['c1'], [], [], extra)
        self._ts_parse(dict(layers=['c1']), ['c1'], [], [], extra)
        self._ts_parse(dict(tables='a'), [], ['a'], [])
        self._ts_parse(dict(tables=['a', 'b']), [], ['a', 'b'], [])
        self._ts_parse(dict(functions='x'), [], [], ['x'])
        self._ts_parse(dict(functions=['x', 'y']), [], [], ['x', 'y'])
        self._ts_parse(dict(layers=['c1'], tables=['a', 'b'], functions=['x', 'y']),
                       ['c1'], ['a', 'b'], ['x', 'y'], extra)

    def _ts_overrides(self, expected_layer: dict,
                      layer: Optional[dict] = None,
                      override_ts: Optional[dict] = None,
                      override_layer: Optional[dict] = None,
                      env: Optional[dict] = None):
        data = parsed_data([Case('my_id', 'my_query;')])

        ts_data = data.data['tileset']
        if override_ts is not None:
            ts_data['overrides'] = override_ts
        if layer is not None:
            ts_data['layers'][0]['file'].data['layer'].update(layer)
        if override_layer is not None:
            ts_data['layers'][0].update(override_layer)

        ts = Tileset(data, getenv=env.get if env else None)
        for k in expected_layer.keys():
            self.assertEqual(getattr(ts.layers_by_id['my_id'], k), expected_layer[k])

    def test_overrides(self):
        buf_0 = dict(buffer_size=0)
        buf_1 = dict(buffer_size=1)
        buf_2 = dict(buffer_size=2)
        buf_3 = dict(buffer_size=3)
        min_1 = dict(min_buffer_size=1)
        min_2 = dict(min_buffer_size=2)
        min_3 = dict(min_buffer_size=3)

        self._ts_overrides(buf_2, buf_2)
        self._ts_overrides(buf_0, buf_2, override_ts=buf_0)
        self._ts_overrides(buf_1, buf_2, override_ts=buf_1)
        self._ts_overrides(buf_3, buf_2, override_ts=buf_3)
        self._ts_overrides(buf_1, min_1 | buf_2, override_ts=buf_0)
        self._ts_overrides(buf_1, buf_2, override_layer=buf_1)
        self._ts_overrides(buf_2, min_2 | buf_3, override_layer=buf_1)
        self._ts_overrides(buf_3, min_1 | buf_2, override_layer=min_3)
        self._ts_overrides(buf_3, min_1 | buf_2, override_layer=min_2 | buf_3, override_ts=buf_0)

        env_0 = dict(TILE_BUFFER_SIZE='0')
        env_2 = dict(TILE_BUFFER_SIZE='2')
        self._ts_overrides(buf_2, min_1 | buf_2, override_layer=min_2 | buf_3, override_ts=buf_0, env=env_0)
        self._ts_overrides(buf_2, buf_1, env=env_2)
        self._ts_overrides(buf_2, min_2 | buf_3, env=env_0)
        self._ts_overrides(buf_2, min_1 | buf_3, override_ts=buf_0, env=env_2)
        self._ts_overrides(buf_2, buf_2, dict(TILE_BUFFER_SIZE=''))

        # str parsing
        self._ts_overrides(dict(buffer_size=2), dict(buffer_size='2'))


if __name__ == '__main__':
    main()
