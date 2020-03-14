import os
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest import IsolatedAsyncioTestCase, main

import asyncpg
import shutil

from openmaptiles.pgutils import PgWarnings

test_dir = Path(__file__).parent

wd_path = shutil.which('import-wikidata')
if not wd_path:
    wd_path = shutil.which('import-wikidata', path=test_dir / '../../bin')
    if not wd_path:
        raise ValueError("Unable to locate import-wikidata script")

importer = SourceFileLoader('import-wikidata', wd_path).load_module()


class UtilsTestCase(IsolatedAsyncioTestCase):

    async def test_find_tables(self):
        tables = importer.find_tables(test_dir / '../testlayers/testmaptiles.yaml')
        self.assertEqual(tables, ['osm_housenumber_point'])

    async def test_pg_func(self):
        conn = None
        try:
            conn = await asyncpg.connect(
                database=os.getenv('PGDATABASE'),
                host=os.getenv('PGHOST'),
                port=os.getenv('PGPORT'),
                user=os.getenv('PGUSER'),
                password=os.getenv('PGPASSWORD'),
            )
            PgWarnings(conn)
            await conn.set_builtin_type_codec('hstore', codec_name='pg_contrib.hstore')

            # TODO: implement some tests
            print("WARNING: import-wikidata PostgreSQL tests are not yet implemented")

        finally:
            if conn:
                await conn.close()


if __name__ == '__main__':
    main()
