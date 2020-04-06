import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

import asyncpg

from openmaptiles.pgutils import get_postgis_version, get_vector_layers
from openmaptiles.sqlite_utils import query
from openmaptiles.sqltomvt import MvtGenerator
from openmaptiles.tileset import Tileset
from openmaptiles.utils import print_err, Bbox


class KeyFinder:

    def __init__(self,
                 mbtiles,
                 show_size=None,
                 show_examples=None,
                 outfile: str = None,
                 zoom=None,
                 verbose=False) -> None:
        self.mbtiles = mbtiles
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
            with self.outfile.open("w"):
                pass  # create or truncate file, but don't write anything to it yet
        with sqlite3.connect(self.mbtiles) as conn:
            results = []
            if self.show_size:
                sql = "SELECT cnt, dups.tile_id, LENGTH(tile_data) FROM (" \
                      "  SELECT tile_id, COUNT(*) as cnt FROM map " \
                      "  GROUP BY tile_id HAVING cnt > ?" \
                      ") dups JOIN images ON images.tile_id = dups.tile_id"
                sql_opts = [self.min_dup_count]
                if self.zoom:
                    sql += f" WHERE zoom_level=?"
                    sql_opts.append(self.zoom)
            else:
                sql_opts = []
                sql = "SELECT COUNT(*) cnt, tile_id FROM map"
                if self.zoom:
                    sql += f" WHERE zoom_level=?"
                    sql_opts.append(self.zoom)
                sql += " GROUP BY tile_id HAVING cnt > ?"
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
                example_sql = "select zoom_level, tile_column, tile_row from map " \
                              "where tile_id = ? limit 5"
                examples = [f'{z}/{x}/{y}' for z, x, y in
                            query(conn, example_sql, [tile_id])]
            if self.verbose:
                res = f"{tile_id} x {count:,}"
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
            with self.outfile.open("a") as f:
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
                with self.outfile.open("w"):
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
                        with self.outfile.open("a") as f:
                            f.writelines(without_key)
                    nokey_tiles += len(without_key)

            if self.verbose:
                for k, c in key_stats.items():
                    print_err(f"{k} - added {c:,}")
                print_err(f'Total imputed tiles: {keyed_tiles:,}')
                if nokey_tiles:
                    print_err(f'Total tiles need to be generated: {nokey_tiles:,}')

    def tile_batches(self, conn: sqlite3.Connection, limit_to_keys=False):
        """Generate batches of tiles to be processed for the new zoom,
        based on the previous zoom level. Each yield contains two batches:
        one with "empty" tiles (those that match known keys),
        and another with non-empty tiles (only if limit_to_keys is False).
        The first batch can be inserted into mbtiles db as is.
        The second batch will be used as a list of tiles to be generated.
        """
        batch_size = 1000000
        zoom = self.zoom
        search_zoom = zoom - 1
        sql = f"select tile_column, tile_row, tile_id from map where zoom_level=?"
        sql_args = [search_zoom]
        if limit_to_keys:
            sql += f" and tile_id IN ({','.join(('?' * len(self.keys)))})"
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
                without_key.append(f"{zoom}/{x * 2}/{ry * 2}\n")
                without_key.append(f"{zoom}/{x * 2 + 1}/{ry * 2}\n")
                without_key.append(f"{zoom}/{x * 2}/{ry * 2 + 1}\n")
                without_key.append(f"{zoom}/{x * 2 + 1}/{ry * 2 + 1}\n")
            if len(with_key) > batch_size or len(without_key) > batch_size:
                yield with_key, without_key
                with_key = []
                without_key = []
        if with_key or without_key:
            yield with_key, without_key


def validate(name, value):
    if name == 'mtime':
        try:
            val = datetime.fromtimestamp(int(value) / 1000.0)
            return f'{value} ({val.isoformat()})', True
        except ValueError:
            return f'{value} (invalid)', False
    elif name in ('filesize', 'maskLevel', 'minzoom', 'maxzoom'):
        try:
            return f'{int(value):,}', True
        except ValueError:
            return f'{value} (invalid)', False
    elif name == 'json':
        try:
            json.loads(value)
            return f'(ok)\n{value}', True
        except ValueError:
            return f'(invalid)\n{value}', False
    return value, True


async def get_minmax(cursor):
    cursor.execute("SELECT MIN(zoom_level), MAX(zoom_level) FROM map")
    min_z, max_z = cursor.fetchone()
    if min_z is None:
        raise ValueError("Unable to get min/max zoom - tile data is empty")
    return min_z, max_z


def update_metadata(cursor, metadata, reset):
    if reset:
        cursor.execute("DELETE FROM metadata;")
    for name, value in metadata.items():
        _, is_valid = validate(name, value)
        if not is_valid:
            raise ValueError(f"Invalid {name}={value}")
        cursor.execute(
            "INSERT OR REPLACE INTO  metadata(name, value) VALUES (?, ?);",
            [name, value])


class Metadata:
    def __init__(self, mbtiles) -> None:
        self.mbtiles = mbtiles

    def print_all(self):
        with sqlite3.connect(self.mbtiles) as conn:
            data = list(query(conn, "SELECT name, value FROM metadata", []))
        if data:
            width = max((len(v[0]) for v in data))
            for name, value in sorted(data, key=lambda v: v[0] if v[0] != 'json' else 'zz'):
                print(f"{name:{width}} {validate(name, value)[0]}")
        else:
            print(f"There are no values present in {self.mbtiles} metadata table")

    def get_value(self, name):
        with sqlite3.connect(self.mbtiles) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM metadata WHERE name=?", [name])
            row = cursor.fetchone()
            if row is None:
                print_err(f"Metadata field '{name}' is not found")
                exit(1)
            print(row[0])

    def set_value(self, name, value):
        _, is_valid = validate(name, value)
        if not is_valid:
            raise ValueError(f"Invalid {name}={value}")
        with sqlite3.connect(self.mbtiles) as conn:
            cursor = conn.cursor()
            if value is None:
                cursor.execute("DELETE FROM metadata WHERE name=?;", [name])
            else:
                cursor.execute(
                    "INSERT OR REPLACE INTO  metadata(name, value) VALUES (?, ?);",
                    [name, value])

    async def generate(self, tileset, reset, auto_minmax,
                       pghost, pgport, dbname, user, password):
        ts = Tileset.parse(tileset)
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

        # Convert tileset to the metadata object according to mbtiles 1.3 spec
        # https://github.com/mapbox/mbtiles-spec/blob/master/1.3/spec.md#content
        metadata = dict(
            # MUST
            name=os.environ.get('METADATA_NAME', ts.name),
            format="pbf",
            json=json.dumps(json_data, ensure_ascii=False, separators=(',', ':')),
            # SHOULD
            bounds=",".join((str(v) for v in ts.bounds)),
            center=",".join((str(v) for v in ts.center)),
            minzoom=os.environ.get('MIN_ZOOM', str(ts.minzoom)),
            maxzoom=os.environ.get('MAX_ZOOM', str(ts.maxzoom)),
            # MAY
            attribution=os.environ.get('METADATA_ATTRIBUTION', ts.attribution),
            description=os.environ.get('METADATA_DESCRIPTION', ts.description),
            version=os.environ.get('METADATA_VERSION', ts.version),
            # EXTRAS
            filesize=os.path.getsize(self.mbtiles),
        )

        bbox_str = os.environ.get('BBOX')
        if bbox_str:
            bbox = Bbox(bbox=bbox_str,
                        center_zoom=os.environ.get('CENTER_ZOOM', ts.center[2]))
            metadata["bounds"] = bbox.bounds_str()
            metadata["center"] = bbox.center_str()

        with sqlite3.connect(self.mbtiles) as conn:
            cursor = conn.cursor()
            if auto_minmax:
                metadata["minzoom"], metadata["maxzoom"] = await get_minmax(cursor)
            update_metadata(cursor, metadata, reset)

        print("The metadata now contains these values:")
        self.print_all()

    def copy(self, target_mbtiles, reset, auto_minmax):
        with sqlite3.connect(self.mbtiles) as conn:
            metadata = {k: v for k, v in
                        query(conn, "SELECT name, value FROM metadata", [])}

        def update_from_env(param, env_var):
            val = os.environ.get(env_var)
            if val is not None:
                metadata[param] = val

        update_from_env('name', 'METADATA_NAME')
        update_from_env('minzoom', 'MIN_ZOOM')
        update_from_env('maxzoom', 'MAX_ZOOM')
        update_from_env('attribution', 'METADATA_ATTRIBUTION')
        update_from_env('description', 'METADATA_DESCRIPTION')
        update_from_env('version', 'METADATA_VERSION')

        metadata['filesize'] = os.path.getsize(target_mbtiles)

        bbox_str = os.environ.get('BBOX')
        if bbox_str:
            bbox = Bbox(bbox=bbox_str,
                        center_zoom=os.environ.get('CENTER_ZOOM'))
            metadata["bounds"] = bbox.bounds_str()
            metadata["center"] = bbox.center_str()

        with sqlite3.connect(target_mbtiles) as conn:
            cursor = conn.cursor()
            if auto_minmax:
                metadata["minzoom"], metadata["maxzoom"] = await get_minmax(cursor)
            update_metadata(cursor, metadata, reset)
        print("The metadata now contains these values:")
        self.print_all()
