import shutil
from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta, datetime
from functools import reduce
from math import ceil
from typing import Tuple, Dict, List

import asyncpg
from ascii_graph import Pyasciigraph
from asyncpg import Connection, UndefinedFunctionError, UndefinedObjectError
from docopt import DocoptExit

from openmaptiles.sqltomvt import MvtGenerator
from openmaptiles.tileset import Tileset
from openmaptiles.utils import round_td


@dataclass
class TestCase:
    id: str
    desc: str
    start: Tuple[int, int]  # inclusive tile coordinate (x,y)
    before: Tuple[int, int]  # exclusive tile coordinate (x,y)
    zoom: int = 14
    layers: str = None
    query: str = None
    duration: timedelta = None
    bytes: int = 0

    def __post_init__(self):
        assert self.id and self.desc
        assert isinstance(self.start, tuple) and isinstance(self.before, tuple)
        assert len(self.start) == 2 and len(self.before) == 2
        assert self.start[0] <= self.before[0] and self.start[1] <= self.before[1]
        assert self.size() > 0 or (self.start == (0, 0) and self.before == (0, 0))

    def make_test(self, zoom, layers, query):
        diff = zoom - self.zoom
        mult = pow(2, diff) if diff > 0 else 1 / pow(2, -diff)
        return TestCase(
            self.id, self.desc,
            (int(self.start[0] * mult), int(self.start[1] * mult)),
            (int(ceil(self.before[0] * mult)), int(ceil(self.before[1] * mult))),
            zoom=zoom, layers=layers, query=query)

    def size(self) -> int:
        return (self.before[0] - self.start[0]) * (self.before[1] - self.start[1])

    def fmt_table(self) -> str:
        pos = ''
        if self.size() > 0:
            pos = f" [{self.start[0]}/{self.start[1]}]" \
                  f"x[{self.before[0] - 1}/{self.before[1] - 1}]"
        res = f"* {self.id:10} {self.desc} ({self.size():,} tiles at z{self.zoom}{pos})"
        return res

    def format(self) -> str:
        if self.layers:
            if len(self.layers) == 1:
                layers = f"layer {self.layers[0]}"
            else:
                layers = f"layers [{','.join(self.layers)}]"
        else:
            layers = 'all layers'
        return f"{layers} test '{self.id}' at zoom {self.zoom} " \
               f"({self.size():,} tiles) - {self.desc}"


class PerfTester:
    # All test cases are defined on z14 by default. Second x,y pair is exclusive.
    # ATTENTION: Do not change tile ranges once they are published
    # Use this site to get tile coordinates (use Google's variant)
    # https://www.maptiler.com/google-maps-coordinates-tile-bounds-projection/
    TEST_CASES: Dict[str, TestCase] = {v.id: v for v in [
        TestCase(
            'us-across',
            'A line from Pacific ocean across US via New York and some Atlantic ocean',
            (2490, 6158), (4851, 6159)),  # DO NOT CHANGE THESE COORDINATES
        TestCase(
            'eu-prague',
            'A region around Prague, CZ',
            (8832, 5536), (8863, 5567)),  # DO NOT CHANGE THESE COORDINATES
        TestCase(
            'ocean',
            'Ocean tiles without much content',
            (8065, 8065), (8302, 8101)),  # DO NOT CHANGE THESE COORDINATES
        TestCase(
            'null',
            'Empty set, useful for query validation.',
            (0, 0), (0, 0)),  # DO NOT CHANGE THESE COORDINATES
    ]}

    def __init__(self, tileset: str, tests: List[str], layers: List[str],
                 zooms: List[int], dbname: str, pghost, pgport: str, user: str,
                 password: str, summary: bool, per_layer: bool, buckets: int,
                 verbose: bool):
        self.tileset = Tileset.parse(tileset)
        self.dbname = dbname
        self.pghost = pghost
        self.pgport = pgport
        self.user = user
        self.password = password
        self.summary = summary
        self.buckets = buckets
        self.verbose = verbose

        for test in tests:
            if test not in self.TEST_CASES:
                cases = '\n'.join(map(TestCase.fmt_table, self.TEST_CASES.values()))
                raise DocoptExit(f"Test '{test}' is not defined. "
                                 f"Available tests are:\n{cases}\n")
        if per_layer and not layers:
            layers = [l["layer"]['id'] for l in self.tileset.layers]
        self.tests = []
        for layer in (layers if per_layer else [None]):
            for test in tests:
                for z in zooms:
                    self.tests.append(self.create_testcase(test, z, layer or layers))

        width = shutil.get_terminal_size((100, 20)).columns
        self.bytes_graph = Pyasciigraph(human_readable='cs', float_format='{:,.1f}',
                                        line_length=width)
        self.speed_graph = Pyasciigraph(float_format='{:,.1f}', line_length=width)

    async def run(self):
        print(f'Connecting to PostgreSQL at {self.pghost}:{self.pgport}, '
              f'db={self.dbname}, user={self.user}...')
        async with asyncpg.create_pool(
            database=self.dbname, host=self.pghost, port=self.pgport, user=self.user,
            password=self.password, min_size=1, max_size=1,
        ) as pool:
            async with pool.acquire() as conn:
                await self.show_settings(conn)
                for testcase in self.tests:
                    await self.run_test(conn, testcase)

        print(f"\n\n================ SUMMARY ================")
        zooms = list({v.zoom for v in self.tests})
        if len(zooms) > 1:
            zooms.sort()
            durations = defaultdict(timedelta)
            tile_sizes = defaultdict(int)
            tile_counts = defaultdict(int)
            for res in self.tests:
                durations[res.zoom] += res.duration
                tile_sizes[res.zoom] += res.bytes
                tile_counts[res.zoom] += res.size()
            speed_data = []
            size_data = []
            for z in zooms:
                info = f"{tile_counts[z]:,} total tiles in " \
                       f"{round_td(durations[z])}"
                speed_data.append((
                    f"tiles/s at z{z}, {info}",
                    float(tile_counts[z]) / durations[z].total_seconds()))
                size_data.append((
                    f"per tile at z{z}, {info}",
                    float(tile_sizes[z]) / tile_counts[z]))
            if len(speed_data) > 1:
                for line in self.speed_graph.graph(f"Per-zoom generation speed",
                                                   speed_data):
                    print(line)
                print()
                for line in self.bytes_graph.graph(f"Per-zoom average tile sizes",
                                                   size_data):
                    print(line)
                print()

        total_duration = reduce(lambda a, b: a + b, (v.duration for v in self.tests))
        total_tiles = reduce(lambda a, b: a + b, (v.size() for v in self.tests))
        total_bytes = reduce(lambda a, b: a + b, (v.bytes for v in self.tests))
        print(f"Generated {total_tiles:,} tiles in {round_td(total_duration)}, "
              f"{total_tiles / total_duration.total_seconds():,.1f} tiles/s, "
              f"{total_bytes / total_tiles:,.1f} bytes per tile.")

    def create_testcase(self, test, zoom, layers):
        mvt = MvtGenerator(self.tileset, layer_ids=layers)
        prefix = 'CAST($1 as int) as z, xval.x as x, yval.y as y,' \
            if not self.summary else 'sum'
        query = f"""\
SELECT {prefix}(COALESCE(LENGTH((
{mvt.generate_query('TileBBox($1, xval.x, yval.y)', '$1')}
)), 0)) AS len FROM
generate_series(CAST($2 as int), CAST($3 as int)) AS xval(x),
generate_series(CAST($4 as int), CAST($5 as int)) AS yval(y);
"""
        return self.TEST_CASES[test].make_test(zoom, layers, query)

    @staticmethod
    async def show_settings(conn: Connection):
        for setting in [
            'version()',
            'postgis_full_version()',
            'shared_buffers',
            'work_mem',
            'max_connections',
            'max_worker_processes',
            'max_parallel_workers',
            'max_parallel_workers_per_gather',
        ]:
            q = f"{'SELECT' if '(' in setting else 'SHOW'} {setting};"
            try:
                res = await conn.fetchval(q)
            except (UndefinedFunctionError, UndefinedObjectError) as ex:
                res = ex.message
            print(f"* {setting:32} = {res}")

    async def run_test(self, conn: Connection, test: TestCase):
        results = []
        print(f"\nRunning {test.format()}...")
        if self.verbose:
            print(f'Using SQL query:\n\n-------\n\n{test.query}\n\n-------\n\n')
        args = [
            test.query,
            test.zoom,
            test.start[0], test.before[0] - 1,
            test.start[1], test.before[1] - 1,
        ]
        start = datetime.utcnow()
        if self.summary:
            test.bytes = await conn.fetchval(*args)
        else:
            for row in await conn.fetch(*args):
                results.append(((row['z'], row['x'], row['y']), row['len']))
                test.bytes += row['len']
        test.duration = datetime.utcnow() - start

        if self.summary:
            size = test.size()
            print(f"Generated {size:,} tiles in {round_td(test.duration)}, "
                  f"average {float(test.bytes) / size if size else 0:,.1f} bytes/tile, "
                  f"{size / test.duration.total_seconds():,.1f} tiles/s")
            return

        tile_count = len(results)
        if tile_count != test.size():
            print(f"WARNING: Requested {test.size():,} tiles != got {tile_count:,}")

        results.sort(key=lambda v: v[1])
        buckets = min(tile_count, self.buckets)
        sums = [0.0] * buckets
        first = [buckets + 1] * buckets
        last = [buckets + 1] * buckets
        last_ind = -1
        for ind, val in enumerate(results):
            i = int(float(ind) / tile_count * buckets)
            sums[i] += val[1]
            last[i] = ind
            if last_ind != i:
                first[i] = ind
                last_ind = i

        data = []
        for i in range(buckets):
            frm = results[first[i]]
            utl = results[last[i]]
            info = f"avg tile size, {frm[1]:,} B ({'/'.join(map(str, frm[0]))}) — " \
                   f"{utl[1]:,} B ({'/'.join(map(str, utl[0]))})"
            data.append((info, (round(sums[i] / (last[i] - first[i] + 1), 1))))

        if not data:
            print(f"Query returned no data after {test.duration}")
            return

        header = f"Tile size distribution for {tile_count:,} generated tiles " \
                 f"({tile_count / buckets:.0f} per line) generated in " \
                 f"{round_td(test.duration)} " \
                 f"({tile_count / test.duration.total_seconds():,.1f} tiles/s)"
        for line in self.bytes_graph.graph(header, data):
            print(line)
