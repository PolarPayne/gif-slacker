import re
from math import log, floor

units_re = re.compile(r"(\d+)([KMG]?B)")
units = {"B": 1, "KB": 10 ** 3, "MB": 10 ** 6, "GB": 10 ** 9}


def parse_bytes(size: str) -> int:
    m = units_re.fullmatch(size)
    number, unit = m[1], m[2]
    return int(number) * units[unit]
