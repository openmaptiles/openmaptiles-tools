from os import getenv
from typing import Dict, List

import asyncpg
from asyncpg import UndefinedFunctionError, UndefinedObjectError, Connection

from openmaptiles.perfutils import COLOR
from openmaptiles.utils import coalesce, print_err


async def get_postgis_version(conn: Connection) -> str:
    try:
        return await conn.fetchval('SELECT postgis_full_version()')
    except (UndefinedFunctionError, UndefinedObjectError):
        raise ValueError('postgis_full_version() does not exist, '
                         'probably because PostGIS is not installed')


async def show_settings(conn: Connection, verbose=True) -> Dict[str, str]:
    settings = {
        'version()': None,
        'postgis_full_version()': None,
        'jit':
            lambda v: 'disable JIT in PG 11+ for complex queries' if v != 'off' else '',
        'shared_buffers': None,
        'work_mem': None,
        'maintenance_work_mem': None,
        'effective_cache_size': None,
        'effective_io_concurrency': None,
        'max_connections': None,
        'max_worker_processes': None,
        'max_parallel_workers': None,
        'max_parallel_workers_per_gather': None,
        'wal_buffers': None,
        'min_wal_size': None,
        'max_wal_size': None,
        'random_page_cost': None,
        'default_statistics_target': None,
        'checkpoint_completion_target': None,
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
                    suffix = f' -- {COLOR.RED}{msg}{COLOR.RESET}'
            results[setting] = res
        except (UndefinedFunctionError, UndefinedObjectError) as ex:
            res = ex.message
            prefix, suffix = COLOR.RED, COLOR.RESET
            results[setting] = None
        if verbose:
            print(f'* {setting:{key_len}} = {prefix}{res}{suffix}')

    return results


def parse_pg_args(args):
    pghost = coalesce(
        args.get('--pghost'), getenv('POSTGRES_HOST'), getenv('PGHOST'),
        'localhost')
    pgport = coalesce(
        args.get('--pgport'), getenv('POSTGRES_PORT'), getenv('PGPORT'),
        '5432')
    dbname = coalesce(
        args.get('--dbname'), getenv('POSTGRES_DB'), getenv('PGDATABASE'),
        'openmaptiles')
    user = coalesce(
        args.get('--user'), getenv('POSTGRES_USER'), getenv('PGUSER'),
        'openmaptiles')
    password = coalesce(
        args.get('--password'), getenv('POSTGRES_PASSWORD'),
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
            print_err(f'  {msg.severity}: {msg.message} @ {msg.context}')
        except AttributeError:
            print_err(f'  {msg}')

    def print(self):
        for msg in self.messages:
            self.print_message(msg)
        self.messages = []


async def get_sql_types(connection: Connection):
    """
    Get Postgres types that we can handle,
    and return the mapping of OSM type id (oid) => MVT style type
    """
    sql_to_mvt_types = dict(
        bool='Boolean',
        text='String',
        int4='Number',
        int8='Number',
    )
    types = await connection.fetch(
        'select oid, typname from pg_type where typname = ANY($1::text[])',
        list(sql_to_mvt_types.keys())
    )
    return {row['oid']: sql_to_mvt_types[row['typname']] for row in types}


async def get_vector_layers(conn, mvt) -> List[dict]:
    pg_types = await get_sql_types(conn)
    vector_layers = []
    for layer_id, layer in mvt.get_layers():
        fields = await mvt.validate_layer_fields(conn, layer_id, layer)
        unknown = {
            name: oid
            for name, oid in fields.items() if oid not in pg_types
        }
        if unknown:
            print(f'Ignoring fields with unknown SQL types (OIDs): '
                  f"[{', '.join([f'{n} ({o})' for n, o in unknown.items()])}]")

        vector_layers.append(dict(
            id=layer.id,
            description=layer.description,
            minzoom=mvt.tileset.minzoom,
            maxzoom=mvt.tileset.maxzoom,
            fields={name: pg_types[type_oid]
                    for name, type_oid in fields.items()
                    if type_oid in pg_types},
        ))

    return vector_layers


def print_query_error(error_msg, err, pg_warnings, verbose, query, layer_sql=None):
    msg = f'####### {error_msg} #######'
    line = '#' * len(msg)
    print(f'{line}\n{msg}\n{line}\n{err.__class__.__name__}: {err}')
    if hasattr(err, 'context') and err.context:
        print(f'context: {err.context}')
    pg_warnings.print()
    if not verbose:
        # Always print failed SQL if the mode is not verbose
        query_msg = f'\n== FULL QUERY\n{query.strip()}'
        if layer_sql:
            query_msg += f'\n\n== MVT SQL\n{layer_sql}'
        print(query_msg)
    print(f'{line}\n')
