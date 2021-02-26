import argparse
import sys

from .utils import parse_bytes, percent, bounded, one_of
from .optimizer import Optimizer


def do_video_to_gif(args: argparse.Namespace) -> int:
    with Optimizer(args.input) as o:
        fps_min = args.fps_min
        if type(fps_min) is float:
            fps_min = max(1, int(o.fps * fps_min))

        size_min = args.size_min
        if type(size_min) is float:
            size_min = max(1, int(o.width * size_min))

        lossy_min, lossy_max = args.lossy_min, args.lossy_max
        if type(lossy_min) is float:
            lossy_min = int(o.LOSSY_MAX * lossy_min)
        if type(lossy_max) is float:
            lossy_max = int(o.LOSSY_MAX * lossy_max)

        return o.optimize(
            args.output,
            max_size=args.max_size,
            fps_min=fps_min,
            size_min=size_min,
            lossy_min=lossy_min,
            lossy_max=lossy_max)


def main() -> int:
    # fmt: off
    parser = argparse.ArgumentParser()
    parser.set_defaults(_do=None)

    subparser = parser.add_subparsers()

    video_to_gif = subparser.add_parser("video-to-gif")
    video_to_gif.set_defaults(_do=do_video_to_gif)
    video_to_gif.add_argument(
        "--fps-min",
        type=one_of(
            bounded(percent, min=0, max=1),
            bounded(int, min=1),
        ),
        default=0.0,
        help="minimum fps of output gif"
    )
    video_to_gif.add_argument(
        "--size-min",
        type=one_of(
            bounded(percent, min=0, max=1),
            bounded(int, min=1),
        ),
        default=0.0,
        help="minimum width of output gif"
    )
    video_to_gif.add_argument(
        "--lossy-max",
        type=one_of(
            bounded(percent, min=0, max=1),
            bounded(int, min=0, max=200),
        ),
        default=200,
        help="maximum value for compression"
    )
    video_to_gif.add_argument(
        "--lossy-min",
        type=one_of(
            bounded(percent, min=0, max=1),
            bounded(int, min=0, max=200),
        ),
        default=0,
        help="minimum value for compression"
    )
    video_to_gif.add_argument("--max-size", type=parse_bytes, default=128 * 1000)
    video_to_gif.add_argument("--output", "-o", default="output.gif")
    video_to_gif.add_argument("input")
    # fmt: on

    args = parser.parse_args()

    if args._do is None:
        parser.print_help()
        return 2

    return args._do(args)


if __name__ == "__main__":
    sys.exit(main())
