import json
from collections import defaultdict
from datetime import timedelta, datetime as dt
from pathlib import Path
from typing import Dict, List, Callable, Any, Union

import asyncpg
from asyncpg import Connection
# noinspection PyProtectedMember
from docopt import DocoptExit

from openmaptiles.perfutils import change, PerfSummary, PerfBucket, \
    PerfRoot, TestCase, print_graph
from openmaptiles.pgutils import show_settings, get_postgis_version
from openmaptiles.sqltomvt import MvtGenerator
from openmaptiles.tileset import Tileset
from openmaptiles.utils import round_td

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
        'A region around Prague of mixed urban and country side, CZ',
        (8832, 5536), (8863, 5567)),  # DO NOT CHANGE THESE COORDINATES
    TestCase(
        'eu-london',
        'A dense urban region around London, UK',
        (8175, 5441), (8192, 5452)),  # DO NOT CHANGE THESE COORDINATES
    TestCase(
        'eu-paris',
        'A dense urban region around Paris with all buildings, FR',
        (8289, 5629), (8307, 5643)),  # DO NOT CHANGE THESE COORDINATES
    TestCase(
        'ocean',
        'Ocean tiles without much content',
        (8065, 8065), (8302, 8101)),  # DO NOT CHANGE THESE COORDINATES
    TestCase(
        'null',
        'Empty set, useful for query validation.',
        (0, 0), (0, 0)),  # DO NOT CHANGE THESE COORDINATES
]}


class PerfTester:
    mvt: MvtGenerator
    test_cases: List[TestCase]

    def __init__(self, tileset: str, tests: List[str], test_all, layers: List[str],
                 zooms: List[int], dbname: str, pghost, pgport: str, user: str,
                 password: str, summary: bool, per_layer: bool, buckets: int,
                 save_to: Union[None, str, Path], compare_with: Union[None, str, Path],
                 key_column: bool, gzip: bool, disable_feature_ids: bool,
                 exclude_layers: bool, verbose: bool, bboxes: List[str]):
        self.tileset = Tileset.parse(tileset)
        self.dbname = dbname
        self.pghost = pghost
        self.pgport = pgport
        self.user = user
        self.password = password
        self.summary = summary
        self.buckets = buckets
        self.key_column = key_column
        self.gzip = gzip
        self.disable_feature_ids = disable_feature_ids
        self.verbose = verbose
        self.per_layer = per_layer
        self.save_to = Path(save_to) if save_to else None
        self.results = PerfRoot()

        if compare_with:
            path = Path(compare_with).resolve()
            with path.open('r', encoding='utf-8') as fp:
                self.old_run: PerfRoot = PerfRoot.from_dict(json.load(fp))
            since = round_td(dt.utcnow() - dt.fromisoformat(self.old_run.created))
            print(f'Comparing results with a previous run created {since} ago: {path}')
        else:
            self.old_run = None

        self.all_test_cases = TEST_CASES.copy()

        # Fake bbox tests as if they were defined, and create names for them
        for bbox_idx, bbox in enumerate(bboxes, start=1):
            tc = TestCase(f'bbox_test_{bbox_idx}', bbox, bbox=bbox)
            self.all_test_cases[tc.id] = tc
            tests.append(tc.id)

        for test in tests:
            if test not in self.all_test_cases:
                cases = '\n'.join(map(TestCase.fmt_table, self.all_test_cases.values()))
                raise DocoptExit(f"Test '{test}' is not defined. "
                                 f'Available tests are:\n{cases}\n')
        if test_all:
            # Do this after validating individual tests, they are ignored but validated
            tests = [v for v in self.all_test_cases.keys() if v != 'null']
        all_layers = [v.id for v in self.tileset.layers]
        if layers and exclude_layers:
            # inverse layers list
            layers = [v for v in all_layers if v not in layers]
        elif not layers and per_layer:
            layers = all_layers
        # Keep the order, but ensure no duplicates
        self.layers = list(dict.fromkeys(layers))
        self.tests = list(dict.fromkeys(tests))
        self.zooms = list(dict.fromkeys(zooms))

    async def run(self):
        print(f'Connecting to PostgreSQL at {self.pghost}:{self.pgport}, '
              f'db={self.dbname}, user={self.user}...')
        async with asyncpg.create_pool(
                database=self.dbname, host=self.pghost, port=self.pgport, user=self.user,
                password=self.password, min_size=1, max_size=1,
        ) as pool:
            async with pool.acquire() as conn:
                self.results.created = dt.utcnow().isoformat()
                self.results.tileset = str(Path(self.tileset.filename).resolve())
                await self._run(conn)
                self.results.tests = [v.result for v in self.test_cases]
                self.save_results()

    async def _run(self, conn: Connection):
        self.results.pg_settings = await show_settings(conn)
        print('\nValidating SQL fields in all layers of the tileset')
        self.mvt = MvtGenerator(
            self.tileset,
            postgis_ver=await get_postgis_version(conn),
            zoom='$1', x='xval.x', y='yval.y',
            use_feature_id=False if self.disable_feature_ids else None,
            gzip=self.gzip,
            key_column=self.key_column,
        )
        self.results.layer_fields = {}
        for layer_id, layer_def in self.mvt.get_layers():
            await self.mvt.validate_layer_fields(conn, layer_id, layer_def)
            self.results.layer_fields[layer_id] = layer_def.get_fields()
        self.test_cases = []
        old_tests = self.old_run.tests if self.old_run else None
        for layer in (self.layers if self.per_layer else [None]):
            for test in self.tests:
                for z in self.zooms:
                    tc = self.create_testcase(test, z, layer or self.layers)
                    if old_tests:
                        tc.old_result = next(
                            (v for v in old_tests
                             if v.id == tc.id and v.layers == tc.layers_id and v.zoom == tc.zoom),
                            None)
                    self.test_cases.append(tc)
        for testcase in self.test_cases:
            await self.run_test(conn, testcase)
        print('\n\n================ SUMMARY ================')
        self.print_summary_graphs('test_summary', lambda t: t.id,
                                  lambda t: f'in test {t.id}', 'Per-test')
        self.print_summary_graphs('zoom_summary', lambda v: str(v.zoom),
                                  lambda t: f'at z{t.zoom}', 'Per-zoom')
        if self.per_layer:
            self.print_summary_graphs('layer_summary', lambda t: t.layers_id,
                                      lambda t: f'at {t.fmt_layers()}', 'Per-layer')
        self.results.summary = PerfSummary(
            duration=sum((v.result.duration for v in self.test_cases), timedelta()),
            tiles=sum(v.size() for v in self.test_cases),
            bytes=sum(v.result.bytes for v in self.test_cases),
        )
        print(self.results.summary.perf_format(self.old_run and self.old_run.summary))

    def create_testcase(self, test, zoom, layers) -> TestCase:
        layers = [layers] if isinstance(layers, str) else layers
        self.mvt.set_layer_ids(layers)
        query = self.mvt.generate_sql()
        if self.key_column:
            query = f'SELECT mvt FROM ({query}) AS perfdata'
        prefix = 'CAST($1 as int) as z, xval.x as x, yval.y as y,' \
            if not self.summary else 'sum'
        query = f"""\
SELECT {prefix}(COALESCE(LENGTH(({query})), 0)) AS len FROM
generate_series(CAST($2 as int), CAST($3 as int)) AS xval(x),
generate_series(CAST($4 as int), CAST($5 as int)) AS yval(y);
"""
        return self.all_test_cases[test].make_test(zoom, layers, query)

    async def run_test(self, conn: Connection, test: TestCase):
        results = []
        print(f'\nRunning {test.format()}...')
        if self.verbose:
            print(f'Using SQL query:\n\n-------\n\n{test.query}\n\n-------\n\n')
        args = [
            test.query,
            test.zoom,
            test.start[0], test.before[0] - 1,
            test.start[1], test.before[1] - 1,
        ]
        start = dt.utcnow()
        if self.summary:
            test.result.bytes = await conn.fetchval(*args)
        else:
            for row in await conn.fetch(*args):
                results.append(((row['z'], row['x'], row['y']), row['len']))
                test.result.bytes += row['len']
        test.result.duration = dt.utcnow() - start
        test.result.__post_init__()
        old = test.old_result
        if self.summary:
            print(test.result.perf_format(old))
            return
        if test.size() != len(results):
            print(f'WARNING: Requested {test.size():,} tiles != got {len(results):,}')
        if not results:
            print(f'Query returned no data after {test.result.duration}')
            return

        test.tiles = len(results)
        results.sort(key=lambda v: v[1])
        buckets = min(test.tiles, self.buckets)
        sums = [0] * buckets
        first = [buckets + 1] * buckets
        last = [buckets + 1] * buckets
        last_ind = -1
        for ind, val in enumerate(results):
            i = int(float(ind) / test.tiles * buckets)
            sums[i] += val[1]
            last[i] = ind
            if last_ind != i:
                first[i] = ind
                last_ind = i
        test.result.buckets = []
        for i in range(buckets):
            smallest = results[first[i]]
            largest = results[last[i]]
            test.result.buckets.append(PerfBucket(
                smallest_id='/'.join(map(str, smallest[0])),
                smallest_size=smallest[1],
                largest_id='/'.join(map(str, largest[0])),
                largest_size=largest[1],
                bytes=sums[i],
                tiles=(last[i] - first[i] + 1),
            ))

        old_buckets = old and old.buckets or []
        print_graph(
            f'Tile sizes for {test.tiles:,} tiles '
            f'(~{test.tiles / buckets:.0f}/line) done in '
            f'{round_td(test.result.duration)} '
            f'({test.result.gen_speed:,.1f} tiles/s'
            f"{change(old.gen_speed, test.result.gen_speed, True) if old else ''})",
            [v.graph_msg(old_buckets[ind] if ind < len(old_buckets) else None)
             for ind, v in enumerate(test.result.buckets)],
            is_bytes=True)

    def print_summary_graphs(self, kind, key: Callable[[TestCase], Any],
                             key_fmt: Callable[[TestCase], Any], long_msg):
        groups = {key(v): key_fmt(v) for v in self.test_cases}
        if len(groups) <= 1:
            return  # do not print one-liner graphs
        durations = defaultdict(timedelta)
        tile_sizes = defaultdict(int)
        tile_counts = defaultdict(int)
        for res in self.test_cases:
            durations[key(res)] += res.result.duration
            tile_sizes[key(res)] += res.result.bytes
            tile_counts[key(res)] += res.size()
        stats = {g: PerfSummary(duration=durations[g], tiles=tile_counts[g],
                                bytes=tile_sizes[g]) for g in groups}
        setattr(self.results, kind, stats)
        old_stats = getattr(self.old_run, kind, None) if self.old_run else None

        speed_data = []
        size_data = []
        for grp, grp_desc in groups.items():
            old = old_stats[grp] if old_stats and grp in old_stats else None
            speed_data.append(stats[grp].graph_msg(True, grp_desc, old))
            size_data.append(stats[grp].graph_msg(False, grp_desc, old))

        print_graph(f'{long_msg} generation speed (longer is better)', speed_data)
        print_graph(f'{long_msg} average tile sizes (shorter is better)',
                    size_data, is_bytes=True)

    def save_results(self):
        if self.save_to:
            print(f'Saving results to {self.save_to}')
            with self.save_to.open('w', encoding='utf-8') as fp:
                json.dump(self.results.to_dict(), fp, indent=2)
