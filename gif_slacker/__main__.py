import argparse
import sys

from .utils import parse_bytes
from .optimizer import Optimizer


def main() -> int:
    # fmt: off
    parser = argparse.ArgumentParser()
    parser.add_argument("--fps", type=int, default=1, help="minimum fps of output gif")
    parser.add_argument("--size", type=int, default=24, help="minimum width of output gif")
    parser.add_argument("--lossy", type=int, default=200, help="maximum value for compression")
    parser.add_argument("--max-size", type=parse_bytes, default=128 * 1000)
    parser.add_argument("--output", "-o", default="output.gif")
    parser.add_argument("input")
    # fmt: on

    args = parser.parse_args()

    with Optimizer(args.input) as o:
        return o.optimize(args.output, args.max_size, args.fps, args.size, args.lossy)


if __name__ == "__main__":
    sys.exit(main())
