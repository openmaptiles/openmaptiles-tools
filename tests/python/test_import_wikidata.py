import os
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest import IsolatedAsyncioTestCase, main

import asyncpg
import shutil

from openmaptiles.pgutils import PgWarnings, parse_pg_args

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
