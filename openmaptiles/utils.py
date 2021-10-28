import asyncio
import gzip
import math
import re
import sys
from asyncio.futures import Future
from collections import defaultdict
from datetime import timedelta
from functools import cmp_to_key
from typing import List, Callable, Any, Dict, Awaitable, Iterable, TypeVar, Union, Optional, Tuple

from betterproto import which_one_of
# noinspection PyProtectedMember
from docopt import DocoptExit
from tabulate import tabulate

from openmaptiles.vector_tile import TileFeature, TileLayer, Tile, TileGeomType

T = TypeVar('T')
T2 = TypeVar('T2')


def coalesce(*args):
    """Given a list of values, returns the first one that is not None"""
    for v in args:
        if v is not None:
            return v
    return None


# From https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames#Lon..2Flat._to_tile_numbers_2
def deg2num(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    tile_x = int((lon_deg + 180.0) / 360.0 * n)
    tile_y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return tile_x, tile_y


class Bbox:
    def __init__(self, bbox=None,
                 left=-180.0, bottom=-85.0511, right=180.0, top=85.0511,
                 center_zoom=5) -> None:
        if bbox:
            left, bottom, right, top = bbox.split(',')
        self.min_lon = float(left)
        self.min_lat = float(bottom)
        self.max_lon = float(right)
        self.max_lat = float(top)
        try:
            # Allow both integer and float center zooms
            self.center_zoom = int(center_zoom)
        except ValueError:
            self.center_zoom = float(center_zoom)

    @staticmethod
    def from_geometry(geo):
        """Given GeoJSON geometry, compute the bounding box"""
        bbox = Bbox()
        bbox.min_lon, bbox.max_lon = bbox.max_lon, bbox.min_lon
        bbox.min_lat, bbox.max_lat = bbox.max_lat, bbox.min_lat

        def minmax(vals):
            if isinstance(vals[0], List):
                for v in vals:
                    minmax(v)
            else:
                lon, lat = vals
                if lon < bbox.min_lon:
                    bbox.min_lon = lon
                if lon > bbox.max_lon:
                    bbox.max_lon = lon
                if lat < bbox.min_lat:
                    bbox.min_lat = lat
                if lat > bbox.max_lat:
                    bbox.max_lat = lat

        minmax(geo)
        return bbox

    @staticmethod
    def from_polygon(content: str):
        lines = content.strip().splitlines()[2:][:-2]
        coords = [re.split(r'[\s\t]+', v.strip()) for v in lines]
        return Bbox.from_geometry(
            [[float(v[0]), float(v[1])] for v in coords if len(v) == 2])

    def bounds_str(self):
        return ','.join(map(str, self.bounds()))

    def bounds(self):
        return self.min_lon, self.min_lat, self.max_lon, self.max_lat

    def center_str(self, precision=1):
        return ','.join(map(lambda v: str(round(v, precision)), self.center()))

    def center(self):
        return (
            (self.min_lon + self.max_lon) / 2.0,
            (self.min_lat + self.max_lat) / 2.0,
            self.center_zoom)

    def to_tiles(self, zoom: int):
        """Convert current bbox into (min_x, min_y, max_x, max_y) tile coordinates for a given zoom.
        The result is inclusive for both the min and the max coordinates"""
        max_val = 2 ** zoom - 1

        def limit(v):
            return min(max_val, max(0, v[0])), min(max_val, max(0, v[1]))

        x1, y1 = limit(deg2num(self.min_lat, self.min_lon, zoom))
        x2, y2 = limit(deg2num(self.max_lat, self.max_lon, zoom))
        return min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2),


class Action:
    _result: Future = None

    def __init__(self, action_id: str, depends_on: List[str] = None):
        self.action_id = action_id
        self.depends_on = depends_on or []


async def run_actions(actions: List[Action],
                      executor: Callable[[Action, List[Any]], Awaitable[Any]],
                      ignore_unknown: bool = False,
                      verbose: bool = False):
    """
    Executes all actions in parallel. If action lists dependencies,
    make sure dependent actions finish running first.
    :param actions: list of Action objects, each action having a unique ID, and
        with optional depends_on being an array of other action IDs that must complete
        before this action executes. The action._result is a Future.
        All other values will be ignored (could be used by executor).
    :param executor: runs a single action. Must return a future or be an async func.
        The returned is set as each action's result.
    :param ignore_unknown ignore when dependency ID is not found in actions
    :param verbose print additional debugging info
    :return: all action results
    """
    lookup = _validate_actions(actions, ignore_unknown)

    async def _run(action):
        # noinspection PyProtectedMember
        values = [lookup[v]._result for v in action.depends_on]
        if values:
            values = await asyncio.gather(*values)
        return await executor(action, values)

    # _run() doesn't execute until after this loop is done,
    # and by that time all action results will be set.
    for act in actions:
        act._result = asyncio.ensure_future(_run(act))

    return await asyncio.gather(*[v._result for v in actions])


def _validate_actions(
        actions: List[Action],
        remove_missing_deps=False,
        verbose=False,
) -> Dict[str, Action]:
    """
    Make sure there is no infinite loop, and all IDs exist and not duplicated
    :return dictionary of action IDs and corresponding action objects
    """
    duplicates = find_duplicates([v.action_id for v in actions])
    if duplicates:
        raise ValueError(f"Found duplicate action IDs: {', '.join(duplicates)}")

    lookup = {v.action_id: v for v in actions}
    pending = set(lookup.keys())
    last_pending_count = 0
    while len(pending) != last_pending_count:
        last_pending_count = len(pending)
        for action_id in list(pending):
            action = lookup[action_id]
            for dep in list(action.depends_on):
                if dep not in lookup:
                    msg = f"Action '{action.action_id}' depends " \
                          f"on an undefined action '{dep}'"
                    if remove_missing_deps:
                        if verbose:
                            print(f'{msg} [ignoring]')
                        action.depends_on.remove(dep)
                    else:
                        raise ValueError(msg)
                elif dep in pending:
                    break
            else:
                pending.remove(action_id)
    if pending:
        raise ValueError(f"Found circular dependencies between {', '.join(pending)}")
    return lookup


def find_duplicates(ids: List[str]) -> Iterable[str]:
    if len(set(ids)) == len(ids):
        return []
    return set([v for v in ids if ids.count(v) > 1])


def round_td(delta: timedelta):
    """Round timedelta by first digit after the dot"""
    diff = delta.microseconds
    zero = 1000000 - diff if diff >= 1000000 / 2 else diff
    zero -= int(zero / 100000) * 100000
    s = str(delta - timedelta(microseconds=zero))
    return re.match(r'^([^.]+(\.\d)?)', s).group(1)


def print_err(*args, **kwargs):
    print(*args, **kwargs, file=sys.stderr)


def batches(items: Iterable[T], batch_size: int,
            decorator: Callable[[T], T2] = lambda v: v) -> Iterable[List[T2]]:
    """Given a stream of objects, create a stream of batches of those objects"""
    res = []
    for value in items:
        res.append(decorator(value))
        if len(res) >= batch_size:
            yield res
            res = []
    if res:
        yield res


def parse_zxy_param(param):
    zxy = param.strip()
    if not re.match(r'^\d+[/, ]+\d+[/, ]+\d+$', zxy):
        raise DocoptExit('Invalid <tile_zxy> - must be in the form "zoom/x/y"')
    zoom, x, y = [int(v) for v in re.split(r'[/, ]+', zxy)]
    return zoom, x, y


def parse_tags(feature: TileFeature, layer: TileLayer, show_names: bool,
               summary: bool) -> dict:
    if summary:
        show_names = True
    geo_size = len(feature.geometry)
    res = {'*ID*': feature.id,
           'GeoSize': f'{geo_size :,}' if not summary else geo_size,
           'GeoType': TileGeomType(feature.type).name}
    tags = {
        layer.keys[feature.tags[i]]:
            which_one_of(layer.values[feature.tags[i + 1]], 'val')[1] for i in
        range(0, len(feature.tags), 2) if
        show_names or not layer.keys[feature.tags[i]].startswith('name:')}
    if summary:
        res['tags'] = tags
    else:
        res.update(tags)
    return res


def dict_comparator(keys: List[str]):
    """Returns a key= comparator function that decides which of two dictionaries (rows) should be shown first.
    Basic logic: sort first by the type of a value, followed by the value itself.
    Try to parse a str value as an int and a float."""
    type_priorities = {type(None): 0, bool: 1, int: 2, float: 3, str: 4}

    def get_val_type(value: dict, key: str) -> Tuple[int, Any]:
        val = value.get(key, None)
        val_type = type_priorities.get(type(val), None)
        if val_type is None:
            val = str(val)
            val_type = 100
        if val_type == 4 or val_type == 100:
            try:
                val = int(val)
                val_type = 2
            except ValueError:
                try:
                    val = float(val)
                    val_type = 3
                except ValueError:
                    pass
        return val_type, val

    def comparator(value1: dict, value2: dict) -> int:
        for key in keys:
            type1, val1 = get_val_type(value1, key)
            type2, val2 = get_val_type(value2, key)
            if type1 != type2:
                return type2 - type1
            if val1 != val2:
                return 1 if val2 < val1 else -1
        return 0

    return cmp_to_key(comparator)


def print_tile(data: bytes, show_names: bool, summary: bool, info: str, sort_output: bool = False) -> None:
    info = shorten_str(info, 60)
    try:
        tile_raw = gzip.decompress(data)
        gzipped_size = len(data)
        info = 'Tile ' + info
    except gzip.BadGzipFile:
        tile_raw = data
        gzipped_size = len(gzip.compress(data))
        info = 'Uncompressed tile ' + info
    tile = Tile().parse(tile_raw)
    print(f'{info} size={len(tile_raw):,} bytes, gzipped={gzipped_size:,} bytes, {len(tile.layers)} layers')
    res = []
    layers = tile.layers
    if sort_output:
        layers.sort(key=lambda v: v.name)
    for layer in layers:
        tags = [parse_tags(f, layer, show_names, summary) for f in layer.features]
        features = len(layer.features)
        if summary:
            geo_size = sum((int(v['GeoSize']) for v in tags))
            geo_stats = defaultdict(int)
            tag_stats = defaultdict(int)
            name_stats = defaultdict(int)
            for tag in tags:
                geo_stats[tag['GeoType']] += 1
                for key in tag['tags'].keys():
                    if key.startswith('name:'):
                        name_stats[key[5:]] += 1
                    else:
                        tag_stats[key] += 1

            def format_stats(stats, show100=False):
                # First show those with 100%, then the rest, keep the order
                stats = sorted(stats.items(), key=lambda v: -v[1] / features)
                return ', '.join(
                    (k + (f'({v / features:.0%})' if show100 or v < features else '')
                     for k, v in stats))

            entry = {
                'Layer': layer.name,
                'Extent': layer.extent,
                'Ver': layer.version,
                'Features': f'{features :,}',
                'GeoType': format_stats(geo_stats),
                'GeoSize': f'{geo_size:,}',
                'AVG GeoSize': f'{geo_size / features:,.1f}',
                'Fields (percentage only if not all features have it)':
                    format_stats(tag_stats),
            }
            if name_stats:
                if show_names:
                    entry[
                        'name:* fields (percentage of features with that language)'] = format_stats(
                        name_stats, True)
                else:
                    entry['name:* fields'] = f'{len(name_stats)} languages'
            res.append(entry)
        else:
            extra = ''
            if not show_names:
                hidden_names = list(sorted({
                    layer.keys[f.tags[i]][5:]
                    for f in layer.features
                    for i in range(0, len(f.tags), 2)
                    if layer.keys[f.tags[i]].startswith('name:')
                }))
                if hidden_names:
                    extra = f', hiding {len(hidden_names)} name:* languages: ' + \
                            ','.join(hidden_names)
            print(f'\n======= Layer {layer.name}: '
                  f'{features} features, extent={layer.extent}, '
                  f'version={layer.version}{extra} =======')
            if sort_output:
                keys = list(tags[0].keys())
                tags.sort(key=dict_comparator(keys))
            print(tabulate(tags, headers='keys'))
    if summary:
        print(tabulate(res, headers='keys', disable_numparse=True,
                       colalign=['left', 'right', 'right', 'right', 'right', 'right']))


def shorten_str(value: str, length: int) -> str:
    return value if len(value) < length else value[:length] + '…'


def parse_zoom_list(zoom: Union[None, str, List[str]],
                    minzoom: Optional[str] = None,
                    maxzoom: Optional[str] = None) -> Optional[List[int]]:
    """Parse a user-provided list of zooms (one or more --zoom parameters),
       or if not given, parse minzoom and maxzoom.  Returns a list of zooms to work on. """
    result = parse_zoom(zoom, is_list=True)
    if not result and minzoom is not None and maxzoom is not None:
        result = list(range(int(minzoom), int(maxzoom) + 1))
    return result


def parse_zoom(zooms: Union[None, str, List[str]], is_list: bool = False) -> Union[None, List[int], int]:
    """Parse a user-provided zoom or a list of zooms (one or more --zoom parameters).
    In some cases a list of zooms could be given even if a single zoom was required"""
    if not zooms:
        return None
    if isinstance(zooms, str):
        zooms = [zooms]
    result = []
    for zoom in zooms:
        try:
            z = int(zoom)
        except ValueError:
            raise ValueError(f"Unable to parse zoom value '{zoom}'")
        if z < 0 or z > 22:
            raise ValueError(f"Invalid zoom value '{zoom}'")
        result.append(z)
    if not is_list and len(zooms) > 1:
        raise ValueError(f"One zoom value was expected, but multiple values were given: [{', '.join(zooms)}]")
    return result if is_list else result[0]
