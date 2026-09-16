import shutil
from pathlib import Path
from unittest import IsolatedAsyncioTestCase, main
import importlib.util
import importlib.machinery

test_dir = Path(__file__).parent

wd_path = shutil.which('import-wikidata')
if not wd_path:
    wd_path = shutil.which('import-wikidata', path=test_dir / '../../bin')
    if not wd_path:
        raise ValueError('Unable to locate import-wikidata script')

# For Python 3.12+
loader = importlib.machinery.SourceFileLoader('import-wikidata', wd_path)
spec = importlib.util.spec_from_file_location(
    'import-wikidata', wd_path, loader=loader
)
if spec is None or spec.loader is None:
    raise ImportError
importer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(importer)


class UtilsTestCase(IsolatedAsyncioTestCase):

    async def test_find_tables(self):
        tables = importer.find_tables(test_dir / '../testlayers/testmaptiles.yaml')
        self.assertEqual(tables, ['osm_housenumber_point', 'osm_peak_point'])

    # async def test_pg_func(self):
    #     conn = None
    #     try:
    #         pghost, pgport, dbname, user, password = parse_pg_args(
    #             dict(args=dict(dict=lambda v: None))
    #         )
    #         conn = await asyncpg.connect(
    #             database=dbname, host=pghost, port=pgport, user=user, password=password,
    #         )
    #         PgWarnings(conn)
    #         await conn.set_builtin_type_codec('hstore', codec_name='pg_contrib.hstore')
    #
    #     finally:
    #         if conn:
    #             await conn.close()


if __name__ == '__main__':
    main()
