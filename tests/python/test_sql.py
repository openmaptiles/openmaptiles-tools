from typing import List, Union, Dict
from unittest import main, TestCase
from tests.python.test_helpers import Case, parsed_data

from openmaptiles.sql import collect_sql, sql_assert_table, sql_assert_func


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


if __name__ == '__main__':
    main()
