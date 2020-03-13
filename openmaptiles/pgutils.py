import re
from os import getenv
from typing import Tuple, Dict, Union

import asyncpg
from asyncpg import UndefinedFunctionError, UndefinedObjectError, Connection

from openmaptiles.perfutils import COLOR
from openmaptiles.utils import coalesce, print_err


async def get_postgis_version(conn: Connection) -> str:
    try:
        return await conn.fetchval("SELECT postgis_full_version()")
    except (UndefinedFunctionError, UndefinedObjectError) as ex:
        raise ValueError("postgis_full_version() does not exist, "
                         "probably because PostGIS is not installed")


async def show_settings(conn: Connection, verbose=True) -> Dict[str, str]:
    settings = {
        'version()': None,
        'postgis_full_version()': None,
        'jit': lambda
            v: 'disable JIT in PG 11-12 for complex queries' if v != 'off' else '',
        'shared_buffers': None,
        'work_mem': None,
        'maintenance_work_mem': None,
        'max_connections': None,
        'max_worker_processes': None,
        'max_parallel_workers': None,
        'max_parallel_workers_per_gather': None,
    }
    key_len = max((len(v) for v in settings))
    results = {}
    for setting, validator in settings.items():
        q = f"{'SELECT' if '(' in setting else 'SHOW'} {setting};"
        prefix = ''
        suffix = ''
        try:
            res = await conn.fetchval(q)
            if validator:
                msg = validator(res)
                if msg:
                    prefix, suffix = COLOR.RED, f" {msg}{COLOR.RESET}"
            results[setting] = res
        except (UndefinedFunctionError, UndefinedObjectError) as ex:
            res = ex.message
            prefix, suffix = COLOR.RED, COLOR.RESET
            results[setting] = None
        if verbose:
            print(f"* {setting:{key_len}} = {prefix}{res}{suffix}")

    return results


def parse_pg_args(args):
    pghost = coalesce(
        args.get("--pghost"), getenv('POSTGRES_HOST'), getenv('PGHOST'),
        'localhost')
    pgport = coalesce(
        args.get("--pgport"), getenv('POSTGRES_PORT'), getenv('PGPORT'),
        '5432')
    dbname = coalesce(
        args.get("--dbname"), getenv('POSTGRES_DB'), getenv('PGDATABASE'),
        'openmaptiles')
    user = coalesce(
        args.get("--user"), getenv('POSTGRES_USER'), getenv('PGUSER'),
        'openmaptiles')
    password = coalesce(
        args.get("--password"), getenv('POSTGRES_PASSWORD'),
        getenv('PGPASSWORD'), 'openmaptiles')
    return pghost, pgport, dbname, user, password


class PgWarnings:
    def __init__(self, conn: Connection, delay_printing=False) -> None:
        self.messages = []
        self.delay_printing = delay_printing
        conn.add_log_listener(lambda _, msg: self.on_warning(msg))

    def on_warning(self, msg: asyncpg.PostgresLogMessage):
        if self.delay_printing:
            self.messages.append(msg)
        else:
            self.print_message(msg)

    @staticmethod
    def print_message(msg: asyncpg.PostgresLogMessage):
        try:
            # noinspection PyUnresolvedReferences
            print_err(f"  {msg.severity}: {msg.message} @ {msg.context}")
        except AttributeError:
            print_err(f"  {msg}")

    def print(self):
        for msg in self.messages:
            self.print_message(msg)
        self.messages = []
