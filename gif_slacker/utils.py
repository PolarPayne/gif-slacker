import re
import typing as t
from argparse import ArgumentTypeError

units_re = re.compile(r"(\d+)([KMG]?B)", re.IGNORECASE)
units = {"b": 1, "kb": 10 ** 3, "mb": 10 ** 6, "gb": 10 ** 9}


def parse_bytes(size: str) -> int:
    m = units_re.fullmatch(size)
    if m is None:
        raise ValueError("bytes value must have one of the following units b, kb, mb, or gb")
    number, unit = m[1], m[2]
    return int(number) * units[unit.lower()]


def percent(v: str) -> float:
    if not v.endswith("%"):
        raise ValueError("percent value must end with a '%'")

    return float(v[:-1]) / 100


def bounded(
    f: t.Callable[[str], t.Union[int, float]],
    *,
    min:t.Optional[float]=None,
    max:t.Optional[float]=None
) -> t.Callable[[str], t.Union[int, float]]:
    def inner(v: str) -> t.Union[int, float]:
        parsed = f(v)
        if min is not None and parsed < min:
            raise ValueError(f"parsed value must be at least {min} but it was {parsed}")
        if max is not None and parsed > max:
            raise ValueError(f"parsed value must be at most {max} but it was {parsed}")
        return parsed

    return inner


def one_of(*fs: t.List[t.Callable[[str], t.Union[int, float]]]) -> t.Callable[[str], t.Union[int, float]]:
    if len(fs) == 0:
        raise ValueError("at least one option must be given")

    def inner(v: str) -> t.Union[int, float]:
        last_error = None
        for f in fs:
            try:
                return f(v)
            except (ArgumentTypeError, TypeError, ValueError) as e:
                last_error = e
                continue

        if last_error is not None:
            raise last_error

        raise RuntimeError("unreachable")

    return inner
