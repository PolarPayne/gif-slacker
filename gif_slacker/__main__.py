import argparse
import sys
from shutil import which
from decimal import Decimal

from .utils import parse_bytes, percent, bounded, one_of, time, Percent
from .optimizer import Optimizer


def tools() -> bool:
    if which("ffmpeg") is None:
        print("could not find ffmpeg from path")
        return False

    if which("ffprobe") is None:
        print("could not find ffprobe from path")
        return False

    if which("gifsicle") is None:
        print("could not find gifsicle from path")
        return False

    return True


def do_video_to_gif(args: argparse.Namespace) -> int:
    with Optimizer(args.input) as o:
        if args.info:
            print(f"size: {o.width:>5}")
            print(f"fps:  {o.fps:>5}")
            return 0


        fps_min, fps_max = args.fps_min, args.fps_max
        if type(fps_min) is Percent:
            fps_min = o.fps * fps_min
        if type(fps_max) is Percent:
            fps_max = o.fps * fps_max

        size_min, size_max = args.size_min, args.size_max
        if type(size_min) is Percent:
            size_min = int(o.width * size_min)
        if type(size_max) is Percent:
            size_max = int(o.width * size_max)

        lossy_min, lossy_max = args.lossy_min, args.lossy_max
        if type(lossy_min) is Percent:
            lossy_min = int(o.LOSSY_MAX * lossy_min)
        if type(lossy_max) is Percent:
            lossy_max = int(o.LOSSY_MAX * lossy_max)

        return o.optimize(
            args.output,
            output_size_limit=args.output_size_limit,
            fps_min=fps_min,
            fps_max=fps_max,
            size_min=size_min,
            size_max=size_max,
            lossy_min=lossy_min,
            lossy_max=lossy_max,
            trials=args.trials,
            timeout=args.timeout,
            jobs=args.jobs,
        )


def main() -> int:
    ok = tools()
    if not ok:
        return 3

    # fmt: off
    parser = argparse.ArgumentParser()
    parser.set_defaults(_do=None)

    subparser = parser.add_subparsers()

    video_to_gif = subparser.add_parser("video-to-gif")
    video_to_gif.set_defaults(_do=do_video_to_gif)

    video_to_gif.add_argument(
        "--fps-min",
        type=one_of(
            bounded(percent, min_gt=0, max=1),
            bounded(int, min=1),
            bounded(float, min_gt=0)
        ),
        default=1,
        help="minimum fps of output gif"
    )
    video_to_gif.add_argument(
        "--fps-max",
        type=one_of(
            bounded(percent, min_gt=0, max=1),
            bounded(int, min=1),
            bounded(float, min_gt=0)
        ),
        default=Percent(1.0),
        help="maximum fps of output gif"
    )

    video_to_gif.add_argument(
        "--size-min",
        type=one_of(
            bounded(percent, min=0, max=1),
            bounded(int, min=1),
        ),
        default=8,
        help="minimum width of output gif"
    )
    video_to_gif.add_argument(
        "--size-max",
        type=one_of(
            bounded(percent, min=0, max=1),
            bounded(int, min=1),
        ),
        default=Percent(1.0),
        help="maximum width of output gif"
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
        "--trials", "-n",
        type=int,
        default=None,
        help="number of trials to run, if not set the optimization will run until stopped"
    )
    video_to_gif.add_argument(
        "--timeout", "-t",
        type=time,
        default=None,
        help="maximum time to run the optimization for"
    )
    video_to_gif.add_argument(
        "--jobs", "-j",
        type=int,
        default=1,
        help="number of jobs to run during optimization (set to -1 to use the number of cores)"
    )

    video_to_gif.add_argument(
        "--output", "-o",
        default="output.gif"
    )
    video_to_gif.add_argument(
        "--output-size-limit", "-s",
        type=parse_bytes,
        default=parse_bytes("128kb")
    )

    video_to_gif.add_argument(
        "--info", "-i",
        action="store_true",
    )

    video_to_gif.add_argument("input")
    # fmt: on

    args = parser.parse_args()

    if args._do is None:
        parser.print_help()
        return 2

    return args._do(args)


if __name__ == "__main__":
    sys.exit(main())
