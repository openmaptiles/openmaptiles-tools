import json
import sqlite3
from datetime import datetime
from pathlib import Path

from openmaptiles.sqlite_utils import query
from openmaptiles.utils import print_err


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
                print_err(f'Total changes made - {keyed_tiles}')
                if nokey_tiles:
                    print_err(f'Total tiles need to be generated - {nokey_tiles}')

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


class Metadata():
    def __init__(self, mbtiles) -> None:
        self.mbtiles = mbtiles

    def validate(self, name, value):
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

    def print_all(self):
        with sqlite3.connect(self.mbtiles) as conn:
            data = list(query(conn, "SELECT name, value FROM metadata", []))
        width = max((len(v[0]) for v in data))
        for name, value in sorted(data, key=lambda v: v[0] if v[0] != 'json' else 'zz'):
            print(f"{name:{width}} {self.validate(name, value)[0]}")

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
        _, is_valid = self.validate(name, value)
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
