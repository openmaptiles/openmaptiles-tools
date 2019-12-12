import asyncio
import re
import sys
from asyncio.futures import Future
from datetime import timedelta
from typing import List, Callable, Any, Dict, Awaitable, Iterable, TypeVar

from openmaptiles.consts import *

T = TypeVar('T')
T2 = TypeVar('T2')


def coalesce(*args):
    """Given a list of values, returns the first one that is not None"""
    for v in args:
        if v is not None:
            return v
    return None


class Bbox:
    def __init__(self, bbox=None,
                 left=BBOX_LEFT, bottom=BBOX_BOTTOM, right=BBOX_RIGHT, top=BBOX_TOP,
                 center_zoom=CENTER_ZOOM) -> None:
        if bbox:
            left, bottom, right, top = bbox.split(',')
        self.min_lon = float(left)
        self.min_lat = float(bottom)
        self.max_lon = float(right)
        self.max_lat = float(top)
        self.center_zoom = center_zoom

    def bounds_str(self):
        return ','.join(map(str, self.bounds()))

    def bounds(self):
        return self.min_lon, self.min_lat, self.max_lon, self.max_lat

    def center_str(self):
        return ','.join(map(str, self.center()))

    def center(self):
        return (
            (self.min_lon + self.max_lon) / 2.0,
            (self.min_lat + self.max_lat) / 2.0,
            self.center_zoom)


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
                            print(f"{msg} [ignoring]")
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
