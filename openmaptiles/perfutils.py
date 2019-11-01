import shutil
from dataclasses import dataclass, field
from datetime import timedelta
from math import ceil
from sys import stdout
from typing import Union, List, Dict, Any, Tuple

# noinspection PyUnresolvedReferences
from ascii_graph import Pyasciigraph
# noinspection PyUnresolvedReferences
from dataclasses_json import dataclass_json, config

from openmaptiles.utils import round_td

if stdout.isatty:
    GREEN = "\x1b[32;107m"
    RED = "\x1b[31;107m"
    RESET = "\x1b[0m"
else:
    GREEN, RED, RESET = '', '', ''


def change(old, new, more_is_better=False, color=False):
    growth = (new - old) / new if new != 0 else 0
    if growth == 0:
        clr = None
        value = f" (no change)"
    elif abs(growth) < 0.1:
        # Small change, show the number but don't highlight
        clr = None
        value = f" {growth:+.1%}"
    else:
        clr = GREEN if (growth > 0) == more_is_better else RED
        value = f" {clr}{growth:+.1%}{RESET}"
    if color:
        return value, clr
    else:
        return value


@dataclass
@dataclass_json
class PerfSummary:
    duration: timedelta = field(
        default=None,
        metadata=config(
            encoder=timedelta.total_seconds,
            decoder=lambda v: timedelta(seconds=v),
        ))
    tiles: int = 0
    bytes: int = 0
    tile_avg_size: float = 0
    gen_speed: float = 0

    def __post_init__(self):
        self.tile_avg_size = float(self.bytes) / self.tiles if self.tiles else 0
        if self.duration:
            self.gen_speed = float(self.tiles) / self.duration.total_seconds()

    def perf_format(self, old: 'PerfSummary'):
        if self.tiles > 0:
            return (
                f"Generated {self.tiles:,} tiles in {round_td(self.duration)}, "
                f"{self.gen_speed:,.1f} tiles/s"
                f"{change(old.gen_speed, self.gen_speed, True) if old else ''}"
                f", "
                f"{self.tile_avg_size:,.1f} bytes per tile"
                f"{change(old.tile_avg_size, self.tile_avg_size) if old else ''}"
            )
        else:
            return f"No tiles were generated in {round_td(self.duration)}"

    def graph_msg(self, speed, group, old: 'PerfSummary'):
        info = f"{self.tiles} tiles in {round_td(self.duration)}"
        value = self.gen_speed if speed else self.tile_avg_size
        old = (old.gen_speed if speed else old.tile_avg_size) if old else None
        if old:
            delta, color = change(old, value, color=True, more_is_better=speed)
        else:
            delta = ''
            color = None
        msg = f"{'tiles/s' if speed else 'per tile'}{delta} {group}, {info}"
        if color:
            return msg, value, color
        else:
            return msg, value


@dataclass
@dataclass_json
class PerfBucket:
    smallest_id: str = None
    smallest_size: int = None
    largest_id: str = None
    largest_size: int = None
    tiles: int = 0
    bytes: int = 0
    tile_avg_size: float = 0

    def __post_init__(self):
        self.tile_avg_size = float(self.bytes) / self.tiles if self.tiles else 0

    def graph_msg(self, old: 'PerfBucket'):
        if old:
            delta, color = change(old.tile_avg_size, self.tile_avg_size, color=True)
        else:
            delta = ''
            color = None
        msg = f"avg tile size" \
              f"{delta}, " \
              f"{self.smallest_size:,} B ({self.smallest_id}) — " \
              f"{self.largest_size:,} B ({self.largest_id})"
        if color:
            return msg, self.tile_avg_size, color
        else:
            return msg, self.tile_avg_size


@dataclass
@dataclass_json
class PerfTestSummary(PerfSummary):
    id: str = None
    layers: str = None
    zoom: str = None
    buckets: Union[None, List[PerfBucket]] = None


@dataclass
@dataclass_json
class PerfRoot:
    created: str = None
    tileset: str = None
    settings: Dict[str, str] = field(default_factory=dict)
    layers: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    tests: List[PerfTestSummary] = None
    summary: PerfSummary = None
    zoom_summary: Dict[str, PerfSummary] = field(default_factory=dict)
    layer_summary: Dict[str, PerfSummary] = field(default_factory=dict)


@dataclass
class TestCase:
    id: str = None
    desc: str = None
    start: Tuple[int, int] = None  # inclusive tile coordinate (x,y)
    before: Tuple[int, int] = None  # exclusive tile coordinate (x,y)
    zoom: int = 14
    layers: List[str] = None
    layers_id: str = None
    query: str = None
    old_result: PerfTestSummary = None
    result: PerfTestSummary = None

    def __post_init__(self):
        assert self.id and self.desc
        assert isinstance(self.start, tuple) and isinstance(self.before, tuple)
        assert len(self.start) == 2 and len(self.before) == 2
        assert self.start[0] <= self.before[0] and self.start[1] <= self.before[1]
        assert self.size() > 0 or (self.start == (0, 0) and self.before == (0, 0))
        if self.layers:
            if len(self.layers) == 1:
                self.layers_id = self.layers[0]
            else:
                self.layers_id = ','.join(self.layers)
        else:
            self.layers_id = '_all_'

    def make_test(self, zoom, layers, query):
        diff = zoom - self.zoom
        mult = pow(2, diff) if diff > 0 else 1 / pow(2, -diff)
        tc = TestCase(
            id=self.id, desc=self.desc,
            start=(int(self.start[0] * mult), int(self.start[1] * mult)),
            before=(int(ceil(self.before[0] * mult)), int(ceil(self.before[1] * mult))),
            zoom=zoom, layers=layers, query=query)
        tc.result = PerfTestSummary(id=tc.id, tiles=tc.size(), layers=tc.layers_id,
                                    zoom=zoom)
        return tc

    def size(self) -> int:
        return (self.before[0] - self.start[0]) * (self.before[1] - self.start[1])

    def fmt_table(self) -> str:
        pos = ''
        if self.size() > 0:
            pos = f" [{self.start[0]}/{self.start[1]}]" \
                  f"x[{self.before[0] - 1}/{self.before[1] - 1}]"
        return f"* {self.id:10} {self.desc} ({self.size():,} " \
               f"tiles at z{self.zoom}{pos})"

    def format(self) -> str:
        return f"{self.fmt_layers()} test '{self.id}' at zoom {self.zoom} " \
               f"({self.size():,} tiles) - {self.desc}"

    def fmt_layers(self):
        if self.layers:
            if len(self.layers) == 1:
                return f"layer {self.layers[0]}"
            else:
                vals = ','.join(self.layers)
                return f"layers [{vals}]"
        else:
            return 'all layers'


def print_graph(header, data, is_bytes=False):
    graph = Pyasciigraph(
        float_format='{:,.1f}',
        min_graph_length=20,
        separator_length=1,
        line_length=shutil.get_terminal_size((100, 20)).columns,
        human_readable='cs' if is_bytes else None)
    for line in graph.graph(header, data):
        print(line)
    print()
