import sys
import typing as t
from math import floor, sqrt
from collections import namedtuple

MinMax = namedtuple("MinMax", ["min", "max"])
Vals = namedtuple("Vals", ["fps", "size", "lossy", "distance"])


class UnsatisfiableConstraints(Exception):
    pass


def delta(mima: MinMax, x: int) -> float:
    div = abs(mima.min - mima.max)
    if div == 0:
        return 1.0
    return abs(mima.min - x) / div


def values(fps: MinMax, size: MinMax, lossy: MinMax) -> t.Generator[Vals, bool, Vals]:
    found_params = []
    vals = []

    for fps_ in range(fps.min, fps.max + 1):
        for size_ in range(size.min, size.max + 1):
            for lossy_ in range(lossy.min, lossy.max + 1):
                # fps should affect file size linearly
                dist_fps = delta(fps, fps_)

                # image size should affect file size exponentially
                dist_size = delta(size, size_)
                dist_size **= 0.5

                # compression is likely to affect file size logarithmically
                dist_lossy = abs(1 - delta(lossy, lossy_))
                dist_lossy **= 2.0

                dist = dist_fps + dist_size + dist_lossy

                m = Vals(
                    fps_,
                    size_,
                    lossy_,
                    dist,
                )
                vals.append(m)

    vals.sort(key=lambda v: v.distance, reverse=True)

    while len(vals) > 1:
        median = floor(len(vals) / 2)
        m = vals[median]
        ok = yield m
        if ok:
            vals = vals[:median]
            found_params.append(m)
        else:
            vals = vals[median:]

    if not found_params:
        raise UnsatisfiableConstraints()

    return found_params[-1]
