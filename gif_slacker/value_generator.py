import sys
import typing as t
from math import floor, log
from collections import namedtuple

MinMax = namedtuple("MinMax", ["min", "max"])
Vals = namedtuple("Vals", ["fps", "size", "lossy", "distance"])


class UnsatisfiableConstraints(Exception):
    pass


def values(fps: MinMax, size: MinMax, lossy: MinMax) -> t.Generator[Vals, bool, Vals]:
    m = Vals(fps.max, size.max, lossy.min, 1)
    print(f"yielding the maximum options", file=sys.stderr)
    ok = yield m
    if ok:
        return m

    found_params = []

    m = Vals(fps.min, size.min, lossy.max, 0)
    print(f"yielding the minimum options", file=sys.stderr)
    found_params.append(m)
    ok = yield m
    if not ok:
        print(f"minimum options did not generate a small enough gif", file=sys.stderr)
        raise UnsatisfiableConstraints()

    delta_lossy = abs(lossy.max - lossy.min)

    vals = []
    for fps_ in range(fps.min, fps.max + 1):
        for size_ in range(size.min, size.max + 1):
            for lossy_ in range(lossy.min, lossy.max + 1):
                # fps should affect file size linearly
                dist_fps = fps_ / fps.max
                # assert 0 <= dist_fps <= 1, f"{dist_fps=}"

                # image size should affect file size exponentially
                d_size = size_ / size.max
                dist_size = pow(2, d_size) - 1
                # assert 0 <= dist_size <= 1, f"{dist_size=}"

                # compression is likely to affect file size logarithmically
                cor = abs((lossy.min + lossy_) - 200)
                dist_lossy = 0 if cor == 0 else pow(cor / delta_lossy, 0.5)
                # assert 0 <= dist_lossy <= 1, f"{dist_lossy=}"

                m = Vals(
                    fps_,
                    size_,
                    lossy_,
                    (dist_fps ** 2 + dist_size ** 2 + dist_lossy ** 2) ** (1 / 3),
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

    return found_params[-1]
