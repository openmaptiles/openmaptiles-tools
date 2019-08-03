from .consts import *


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
