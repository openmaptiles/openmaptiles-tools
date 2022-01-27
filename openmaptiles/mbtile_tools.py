import json
import os
import sqlite3
from datetime import datetime
from os import getenv
from pathlib import Path
from sqlite3 import Cursor
from typing import Dict, List, Optional, Tuple

import asyncpg
from tabulate import tabulate

from openmaptiles.pgutils import get_postgis_version, get_vector_layers
from openmaptiles.sqlite_utils import query
from openmaptiles.sqltomvt import MvtGenerator
from openmaptiles.tileset import Tileset
from openmaptiles.utils import print_err, Bbox, print_tile, shorten_str


class KeyFinder:
    """Search mbtiles for frequently used duplicate tiles"""

    def __init__(self,
                 mbtiles,
                 show_size=None,
                 show_examples=None,
                 outfile: str = None,
                 zoom=None,
                 min_dup_count=None,
                 verbose=False) -> None:
        self.mbtiles = mbtiles
        if min_dup_count is not None:
            min_dup_count = int(min_dup_count)
            if min_dup_count < 2:
                raise ValueError('min_dup_count must be an integer ≥ 2')
            self.min_dup_count = min_dup_count
        else:
            self.min_dup_count = 50 if zoom and zoom > 12 else 20
        self.use_stdout = outfile == '-'
        self.zoom = zoom
        self.verbose = verbose
        if outfile:
            self.outfile = True if self.use_stdout else Path(outfile)
        else:
            self.outfile = None
        self.show_size = self.verbose if show_size is None else show_size
        self.show_examples = self.verbose if show_examples is None else show_examples

    def run(self):
        if self.outfile and not self.use_stdout:
            with self.outfile.open('w'):
                pass  # create or truncate file, but don't write anything to it yet
        with sqlite3.connect(self.mbtiles) as conn:
            results = []
            if self.show_size:
                sql = 'SELECT cnt, dups.tile_id, LENGTH(tile_data) FROM (' \
                      '  SELECT tile_id, COUNT(*) AS cnt FROM map ' \
                      '  GROUP BY tile_id HAVING cnt >= ?' \
                      ') dups JOIN images ON images.tile_id = dups.tile_id'
                sql_opts = [self.min_dup_count]
                if self.zoom:
                    sql += ' WHERE zoom_level=?'
                    sql_opts.append(self.zoom)
            else:
                sql_opts = []
                sql = 'SELECT COUNT(*) cnt, tile_id FROM map'
                if self.zoom:
                    sql += ' WHERE zoom_level=?'
                    sql_opts.append(self.zoom)
                sql += ' GROUP BY tile_id HAVING cnt >= ?'
                sql_opts.append(self.min_dup_count)
            for vals in query(conn, sql, sql_opts):
                results.append(vals)
            results.sort(reverse=True)
        size = None
        examples = None
        for vals in results:
            if len(vals) == 3:
                count, tile_id, size = vals
            else:
                count, tile_id = vals
            if self.show_examples:
                example_sql = 'SELECT zoom_level, tile_column, tile_row FROM map ' \
                              'WHERE tile_id = ? LIMIT 5'
                examples = [f'{z}/{x}/{y}' for z, x, y in
                            query(conn, example_sql, [tile_id])]
            if self.verbose:
                res = f'{tile_id} x {count:,}'
                if self.show_size:
                    res += f', {size:,} bytes'
                if self.show_examples:
                    res += ', examples: ' + ', '.join(examples)
                print_err(res)

        results = [v[1] for v in results]
        if self.use_stdout:
            for v in results:
                print(v)
        elif self.outfile:
            with self.outfile.open('a') as f:
                f.writelines([str(v) + '\n' for v in results])

        return results


class Imputer:

    def __init__(self, mbtiles, keys, zoom, outfile: str = None,
                 verbose=False) -> None:
        self.mbtiles = mbtiles
        self.keys = {k: 0 for k in keys}
        self.zoom = zoom
        self.use_stdout = outfile == '-'
        self.verbose = verbose or not self.use_stdout
        if outfile:
            self.outfile = True if self.use_stdout else Path(outfile)
        else:
            self.outfile = None

    def run(self):
        with sqlite3.connect(self.mbtiles) as conn:
            limit_to_keys = not self.outfile
            if self.outfile and not self.use_stdout:
                with self.outfile.open('w'):
                    pass  # create or truncate file, but don't write anything to it yet
            keyed_tiles = 0
            nokey_tiles = 0
            cursor = conn.cursor()
            key_stats = self.keys
            for with_key, without_key in self.tile_batches(conn, limit_to_keys):
                without_key.sort()
                if with_key:
                    with_key.sort()
                    for val in with_key:
                        key_stats[val[3]] += 1
                    cursor.executemany(
                        'INSERT OR IGNORE INTO map'
                        '(zoom_level, tile_column, tile_row, tile_id)'
                        ' VALUES(?,?,?,?)',
                        with_key)
                    keyed_tiles += cursor.rowcount
                    conn.commit()
                if without_key:
                    if self.use_stdout:
                        for v in without_key:
                            print(v, end='')
                    else:
                        with self.outfile.open('a') as f:
                            f.writelines(without_key)
                    nokey_tiles += len(without_key)

            if self.verbose:
                for k, c in key_stats.items():
                    print_err(f'{k} - added {c:,}')
                print_err(f'Total imputed tiles: {keyed_tiles:,}')
                if nokey_tiles:
                    print_err(f'Total tiles need to be generated: {nokey_tiles:,}')

    def tile_batches(self, conn: sqlite3.Connection, limit_to_keys=False):
        """Generate batches of tiles to be processed for the new zoom,
        based on the previous zoom level. Each yield contains two batches:
        one with 'empty' tiles (those that match known keys),
        and another with non-empty tiles (only if limit_to_keys is False).
        The first batch can be inserted into mbtiles db as is.
        The second batch will be used as a list of tiles to be generated.
        """
        batch_size = 1000000
        zoom = self.zoom
        search_zoom = zoom - 1
        sql = 'SELECT tile_column, tile_row, tile_id FROM map WHERE zoom_level=?'
        sql_args = [search_zoom]
        if limit_to_keys:
            sql += f" and tile_id IN ({','.join('?' * len(self.keys))})"
            sql_args += self.keys
        with_key = []
        without_key = []
        max_y = 2 ** search_zoom - 1
        for x, y, key in query(conn, sql, sql_args):
            if limit_to_keys or key in self.keys:
                with_key.append((zoom, x * 2, y * 2, key))
                with_key.append((zoom, x * 2 + 1, y * 2, key))
                with_key.append((zoom, x * 2, y * 2 + 1, key))
                with_key.append((zoom, x * 2 + 1, y * 2 + 1, key))
            else:
                # mbtiles uses inverted Y (starts at the bottom)
                ry = max_y - y
                without_key.append(f'{zoom}/{x * 2}/{ry * 2}\n')
                without_key.append(f'{zoom}/{x * 2 + 1}/{ry * 2}\n')
                without_key.append(f'{zoom}/{x * 2}/{ry * 2 + 1}\n')
                without_key.append(f'{zoom}/{x * 2 + 1}/{ry * 2 + 1}\n')
            if len(with_key) > batch_size or len(without_key) > batch_size:
                yield with_key, without_key
                with_key = []
                without_key = []
        if with_key or without_key:
            yield with_key, without_key


class Metadata:
    def __init__(self, mbtiles: str, show_json: bool = False,
                 show_ranges: bool = False) -> None:
        self.mbtiles = mbtiles
        self.show_json = show_json
        self.show_ranges = show_ranges

    def print_all(self, file: str = None):
        file = file or self.mbtiles
        data = self._get_metadata(file)
        if data:
            width = max((len(v) for v in data.keys()))
            for name, value in sorted(data.items(),
                                      key=lambda v: v[0] if v[0] != 'json' else 'zz'):
                print(f'{name:{width}} {self.validate(name, value)[0]}')
        else:
            print(f'There are no values present in {file} metadata table')

        if self.show_ranges:
            with sqlite3.connect(file) as conn:
                sql = """\
SELECT zoom_level, COUNT(*) AS count,
       MIN(tile_column) AS min_column, MAX(tile_column) AS max_column,
       MIN(tile_row) AS min_row, MAX(tile_row) AS max_row
FROM map
GROUP BY zoom_level
"""
                res = []
                for z, cnt, min_x, max_x, min_y, max_y in sorted(query(conn, sql, [])):
                    res.append({
                        'Zoom': z,
                        'Tile count': f'{cnt:,}',
                        'Found tile ranges': f'{min_x},{min_y} x {max_x},{max_y}',
                    })
                print('\n' + tabulate(res, headers='keys'))

    def get_value(self, name):
        with sqlite3.connect(self.mbtiles) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM metadata WHERE name=?', [name])
            row = cursor.fetchone()
            if row is None:
                print_err(f"Metadata field '{name}' is not found")
                exit(1)
            print(row[0])

    def set_value(self, name, value):
        if value is not None:
            _, is_valid = self.validate(name, value)
            if not is_valid:
                raise ValueError(f'Invalid {name}={value}')
        with sqlite3.connect(self.mbtiles) as conn:
            cursor = conn.cursor()
            if value is None:
                cursor.execute('DELETE FROM metadata WHERE name=?;', [name])
            else:
                cursor.execute(
                    'INSERT OR REPLACE INTO metadata(name, value) VALUES (?, ?);',
                    [name, value])

    async def generate(self, tileset, reset, auto_minmax,
                       pghost, pgport, dbname, user, password):
        ts = Tileset.parse(tileset)
        print(
            f'Connecting to PostgreSQL at {pghost}:{pgport}, db={dbname}, user={user}...')
        try:
            async with asyncpg.create_pool(
                    database=dbname, host=pghost, port=pgport, user=user,
                    password=password, min_size=1, max_size=1,
            ) as pool:
                async with pool.acquire() as conn:
                    mvt = MvtGenerator(
                        ts,
                        postgis_ver=await get_postgis_version(conn),
                        zoom='$1', x='$2', y='$3',
                    )
                    json_data = dict(vector_layers=await get_vector_layers(conn, mvt))
        except ConnectionError as err:
            print(f'Unable to connect to Postgres database: {err}')
            raise err

        # Convert tileset to the metadata object according to mbtiles 1.3 spec
        # https://github.com/mapbox/mbtiles-spec/blob/master/1.3/spec.md#content
        metadata = dict(
            # MUST
            name=ts.name,
            format='pbf',
            json=json.dumps(json_data, ensure_ascii=False, separators=(',', ':')),
            # SHOULD
            bounds=','.join((str(v) for v in ts.bounds)),
            center=','.join((str(v) for v in ts.center)),
            minzoom=str(ts.minzoom),
            maxzoom=str(ts.maxzoom),
            # MAY
            attribution=ts.attribution,
            description=ts.description,
            version=ts.version,
            # EXTRAS
            id=ts.id,
        )

        self._update_metadata(metadata, auto_minmax, reset, self.mbtiles,
                              ts.center[2])

    def copy(self, target_mbtiles, reset, auto_minmax):
        metadata = self._get_metadata(self.mbtiles)
        self._update_metadata(metadata, auto_minmax, reset, target_mbtiles)

    def show_tile(self, zoom, x, y, show_names, summary):
        with sqlite3.connect(self.mbtiles) as conn:
            sql = 'SELECT tile_data FROM tiles ' \
                  'WHERE zoom_level=? AND tile_column=? AND tile_row=?'
            for row in query(conn, sql, [zoom, x, y]):
                print_tile(row[0], show_names, summary, f'{zoom}/{x}/{y}')
                break
            else:
                print(f'Tile {zoom}/{x}/{y} not found')

    def _update_metadata(self, metadata, auto_minmax, reset, file, center_zoom=None):
        def update_from_env(param, env_var):
            val = getenv(env_var)
            if val is not None:
                metadata[param] = val

        update_from_env('name', 'METADATA_NAME')
        update_from_env('minzoom', 'MIN_ZOOM')
        update_from_env('maxzoom', 'MAX_ZOOM')
        update_from_env('attribution', 'METADATA_ATTRIBUTION')
        update_from_env('description', 'METADATA_DESCRIPTION')
        update_from_env('version', 'METADATA_VERSION')

        metadata['filesize'] = os.path.getsize(file)

        bbox_str = getenv('BBOX')
        if bbox_str:
            bbox = Bbox(bbox=bbox_str,
                        center_zoom=getenv('CENTER_ZOOM', center_zoom))
            metadata['bounds'] = bbox.bounds_str()
            metadata['center'] = bbox.center_str()

        with sqlite3.connect(file) as conn:
            cursor = conn.cursor()
            if auto_minmax:
                min_z, max_z = self.find_min_max_zoom(cursor)
                if min_z is None:
                    raise ValueError('Unable to get min/max zoom - tile data is empty')
                metadata['minzoom'] = min_z
                metadata['maxzoom'] = max_z
            self._update_metadata_db(cursor, metadata, reset)
            conn.commit()

        print(f'New metadata values in {file}')
        self.print_all(file=file)

    @staticmethod
    def find_min_max_zoom(cursor, db_prefix='') -> Tuple[int, int]:
        cursor.execute(f'SELECT MIN(zoom_level), MAX(zoom_level) FROM {db_prefix}map')
        return cursor.fetchone()

    @staticmethod
    def _get_metadata(file) -> Dict[str, str]:
        with sqlite3.connect(file) as conn:
            return {k: v for k, v in
                    query(conn, 'SELECT name, value FROM metadata', [])}

    def _update_metadata_db(self, cursor, metadata, reset):
        if reset:
            # noinspection SqlWithoutWhere
            cursor.execute('DELETE FROM metadata;')
        for name, value in metadata.items():
            _, is_valid = self.validate(name, value)
            if not is_valid:
                raise ValueError(f'Invalid {name}={value}')
            cursor.execute(
                'INSERT OR REPLACE INTO metadata(name, value) VALUES (?, ?);',
                [name, value])

    def validate(self, name, value):
        is_valid = True
        if name == 'mtime':
            try:
                val = datetime.fromtimestamp(int(value) / 1000.0)
                value = f'{value} ({val.isoformat()})'
            except ValueError:
                is_valid = False
                value = f'{value} (invalid)'
        elif name in ('filesize', 'maskLevel', 'minzoom', 'maxzoom'):
            try:
                value = f'{int(value):,}'
            except ValueError:
                is_valid = False
                value = f'{value} (invalid)'
        elif name == 'json':
            try:
                val = json.loads(value)
                if self.show_json:
                    value = '(valid JSON value)'
                else:
                    value = '(The value is a valid JSON, use --show-json for raw dump)'

                res = []
                for v in val['vector_layers']:
                    desc = ''
                    if 'description' in v:
                        desc = shorten_str(v['description'], 40)
                    fields = []
                    names = []
                    for fld in v['fields'].keys():
                        if fld.startswith('name:'):
                            names.append(fld[5:])
                        else:
                            fields.append(fld)
                    fields_str = ', '.join(v for v in fields)
                    if names:
                        fields_str += f", name:* ({shorten_str(','.join(names), 20)})"
                    res.append({
                        'layer': v['id'],
                        'minZ': v['minzoom'],
                        'maxZ': v['maxzoom'],
                        'fields': fields_str,
                        'description': desc
                    })
                value += '\n\n' + tabulate(res, headers='keys')
                if self.show_json:
                    value += '\n\n'
                    value += json.dumps(val, ensure_ascii=False, indent=2)

            except ValueError:
                is_valid = False
                if self.show_json:
                    value = f'(invalid JSON value)\n{value}'
                else:
                    value = '(invalid JSON value, use --show-json to see it)'
        return value, is_valid


class TileCopier:
    """Copy tile data between mbtile files"""

    def __init__(self,
                 source: Metadata,
                 target: str,
                 zooms: List[int],
                 minzoom: Optional[int],
                 maxzoom: Optional[int],
                 reset: bool,
                 on_conflict: str,
                 auto_minmax: bool,
                 bbox: Optional[Bbox],
                 verbose: bool,
                 ) -> None:
        self.source = source
        self.target = Path(target)
        self.zooms = zooms
        self.minzoom = minzoom
        self.maxzoom = maxzoom
        self.reset = reset
        self.on_conflict = on_conflict
        self.auto_minmax = auto_minmax
        self.bbox = bbox
        self.verbose = verbose

    def run(self):
        if not self.target.exists():
            self.create_new_db()
        print(f'Opening {self.target}')
        with sqlite3.connect(self.target) as conn:
            cursor = conn.cursor()
            self.execute(cursor, 'ATTACH DATABASE ? AS sourceDb', [self.source.mbtiles])
            self.copy_tiles(cursor)
        self.source.copy(self.target, self.reset, self.auto_minmax)

    def copy_tiles(self, cursor):
        sql = f'INSERT OR {self.on_conflict} INTO map SELECT zoom_level, tile_column, tile_row, tile_id FROM sourceDb.map'
        for sql, params in self.iterate_queries(cursor, sql):
            self.execute(cursor, sql, params)

        if not self.zooms and self.minzoom is None and self.maxzoom is None and self.bbox is None:
            sql = f'INSERT OR {self.on_conflict} INTO images SELECT tile_data, tile_id FROM sourceDb.images'
        else:
            sql = f"""\
INSERT OR {self.on_conflict} INTO images
SELECT images.tile_data, images.tile_id
FROM sourceDb.images
  JOIN sourceDb.map
  ON images.tile_id = map.tile_id"""
        for sql, params in self.iterate_queries(cursor, sql):
            self.execute(cursor, sql, params)

    def iterate_queries(self, cursor, sql):
        # For BBOX filter, perform one query per zoom,
        # otherwise run just one query for the whole DB
        if self.bbox:
            if self.zooms:
                zooms = self.zooms
            elif self.minzoom is not None and self.maxzoom is not None:
                zooms = range(self.minzoom, self.maxzoom + 1)
            else:
                print('Detecting zoom levels in the source file')
                min_z, max_z = self.source.find_min_max_zoom(cursor, 'sourceDb.')
                if min_z is None:
                    print('No tile data was found in the source file')
                    raise StopIteration
                print(f'Source file contains tiles for zooms {min_z}..{max_z}')
                if self.minzoom is not None:
                    min_z = max(self.minzoom, min_z)
                if self.maxzoom is not None:
                    max_z = min(self.maxzoom, max_z)
                zooms = range(min_z, max_z + 1)
            sql += ' WHERE zoom_level = ? AND tile_column BETWEEN ? AND ? AND tile_row BETWEEN ? AND ?'
            for zoom in zooms:
                largest_y = 2 ** zoom - 1
                min_x, min_y, max_x, max_y = self.bbox.to_tiles(zoom)
                yield sql, [zoom, min_x, max_x, largest_y - max_y, largest_y - min_y]
        else:
            if self.zooms:
                sql += f" WHERE zoom_level IN ({','.join('?' * len(self.zooms))})"
                yield sql, self.zooms
            elif self.minzoom is not None and self.maxzoom is not None:
                sql += ' WHERE zoom_level BETWEEN ? AND ?'
                yield sql, [self.minzoom, self.maxzoom]
            elif self.minzoom is not None:
                sql += ' WHERE zoom_level >= ?'
                yield sql, [self.minzoom]
            elif self.maxzoom is not None:
                sql += ' WHERE zoom_level <= ?'
                yield sql, [self.maxzoom]
            else:
                yield sql, []

    def create_new_db(self) -> None:
        print(f'Creating a new file {self.target}')
        with sqlite3.connect(self.target) as conn:
            cursor = conn.cursor()
            self.execute(cursor, 'SELECT * FROM sqlite_master')
            row = cursor.fetchone()
            if row is not None:
                raise ValueError(f"Newly created file '{self.target}' is not empty")

            # This forces DB to the smallest possible block size,
            # making overall file smaller.
            self.execute(cursor, 'PRAGMA page_size = 512;')
            self.execute(cursor, 'VACUUM;')

            for sql in sql_create_mbtiles:
                self.execute(cursor, sql)

    def execute(self, cursor: Cursor, sql: str, params=None):
        if self.verbose:
            vals = '  [' + ', '.join((str(v) for v in params)) + ']' if params else ''
            print(f'Executing {sql}{vals}')
        cursor.execute(sql, params if params else [])
        if self.verbose and cursor.rowcount >= 0:
            print(f'{cursor.rowcount} rows were affected')


sql_create_mbtiles = [
    'CREATE TABLE map (zoom_level INTEGER, tile_column INTEGER, tile_row INTEGER, tile_id TEXT);',
    'CREATE TABLE images (tile_data BLOB, tile_id TEXT);',
    """\
CREATE VIEW tiles AS
  SELECT
      map.zoom_level AS zoom_level,
      map.tile_column AS tile_column,
      map.tile_row AS tile_row,
      images.tile_data AS tile_data
  FROM map
  JOIN images ON images.tile_id = map.tile_id;""",
    'CREATE TABLE metadata (name text, value text);',
    'CREATE UNIQUE INDEX map_index ON map (zoom_level, tile_column, tile_row);',
    'CREATE UNIQUE INDEX images_id ON images (tile_id);',
    'CREATE UNIQUE INDEX name ON metadata (name);',
]
