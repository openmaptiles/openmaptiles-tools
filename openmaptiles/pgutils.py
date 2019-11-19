import re
from typing import Tuple, Dict

from asyncpg import UndefinedFunctionError, UndefinedObjectError, Connection

from openmaptiles.perfutils import COLOR


async def show_settings(conn: Connection) -> Tuple[Dict[str, str], bool]:
    postgis_version = False
    results = {}

    def parse_postgis_ver(value) -> None:
        nonlocal postgis_version
        m = re.match(r'POSTGIS="(\d+\.\d+)', value)
        postgis_version = float(m.group(1))

    settings = {
        'version()': None,
        'postgis_full_version()': parse_postgis_ver,
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
        except (UndefinedFunctionError, UndefinedObjectError) as ex:
            res = ex.message
            prefix, suffix = COLOR.RED, COLOR.RESET

        print(f"* {setting:{key_len}} = {prefix}{res}{suffix}")
        results[setting] = res

    return results, postgis_version
