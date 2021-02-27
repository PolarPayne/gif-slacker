import tempfile
import re
import typing as t
import sys
from pathlib import Path
from math import ceil

from .cmd import cmd
from .value_generator import MinMax, values, UnsatisfiableConstraints


fps_re = re.compile(rb"r_frame_rate=(\d+)/(\d+)")
width_re = re.compile(rb"width=(\d+)")
height_re = re.compile(rb"height=(\d+)")


class Optimizer:

    LOSSY_MIN = 0
    LOSSY_MAX = 200

    def __init__(self, video_file: Path, *, dir: Path = None):
        self.video_file = video_file

        self.tmp = Path(tempfile.mkdtemp(dir=dir))
        self.palette = self.tmp / "palette.png"
        self.intermediate = self.tmp / "intermediate.avi"

        self._update_fps_and_size()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        for file in self.tmp.glob("*.gif"):
            file.unlink()

    def _update_fps_and_size(self) -> t.Tuple[int, int]:
        _, stdout, _ = cmd(
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=r_frame_rate,width,height",
            "-of",
            "default=nw=1",
            self.video_file,
        )

        fps = fps_re.search(stdout)
        if fps is None:
            print(stdout, file=sys.stderr)
            raise ValueError("could not get fps of the video")
        self.fps = ceil(int(fps[1]) / int(fps[2]))

        width = width_re.search(stdout)
        if width is None:
            raise ValueError("could not get width of the video")
        self.width = int(width[1])

        height = height_re.search(stdout)
        if height is None:
            raise ValueError("could not get height of the video")
        self.height = int(height[1])

    def _file_name(self, fps, size, lossy=None) -> str:
        if lossy is None:
            return f"{fps}-{size}.gif"
        return f"{fps}-{size}-{lossy}.gif"

    def _create_palette(self):
        if self.palette.exists():
            return

        input_file = self.video_file
        if self.intermediate.exists():
            input_file = self.intermediate

        print("generating palette")

        cmd(
            "ffmpeg",
            "-i",
            input_file,
            "-vf",
            "palettegen",
            self.palette,
            check=True,
        )

    def _create_intermediate(self, fps: int, size: int):
        output_file = self.intermediate
        if output_file.exists():
            return output_file

        print("creating intermediate file for faster processing")

        cmd(
            "ffmpeg",
            "-i",
            self.video_file,
            "-vf",
            f"fps={fps},scale={size}:-1:flags=lanczos",
            output_file,
            check=True,
        )

    def _to_gif_ffmpeg(self, fps: int, size: int):
        input_file = self.video_file
        if self.intermediate.exists():
            input_file = self.intermediate

        output_file = self.tmp / self._file_name(fps, size)
        if output_file.exists():
            return output_file

        # TODO better error handling
        cmd(
            "ffmpeg",
            "-i",
            input_file,
            "-i",
            self.palette,
            "-lavfi",
            f"fps={fps},scale={size}:-1:flags=lanczos,paletteuse",
            "-loop",
            "0",
            output_file,
            check=True,
        )

        return output_file

    def _to_gif(self, fps: int, size: int, lossy: int) -> t.Tuple[Path, int]:
        created_file = self._to_gif_ffmpeg(fps, size)

        output_file = self.tmp / self._file_name(fps, size, lossy)
        if output_file.exists():
            return output_file, output_file.stat().st_size

        # TODO better error handling
        cmd(
            "gifsicle",
            "-O3",
            f"--lossy={lossy}",
            created_file,
            "-o",
            output_file,
            check=True,
        )

        return output_file, output_file.stat().st_size

    def optimize(
        self,
        output_file: str,
        *,
        output_size_limit: int,
        fps_min: int,
        fps_max: int,
        size_min: int,
        size_max: int,
        lossy_min: int,
        lossy_max: int,
    ) -> int:
        if output_size_limit <= 0:
            raise ValueError("output_size_limit must be larger than zero")

        if not (1 <= fps_min <= self.fps):
            raise ValueError(f"fps_min must be between 1 and {self.fps} (inclusive)")
        if not (1 <= fps_max <= self.fps):
            raise ValueError(f"fps_max must be between 1 and {self.fps} (inclusive)")
        if fps_min > fps_max:
            raise ValueError("fps_min must be less than or equal to fps_max")

        if not (1 <= size_min <= self.width):
            raise ValueError(f"size must be between 1 and {self.width} (inclusive)")
        if not (1 <= size_max <= self.width):
            raise ValueError(f"size_max must be between 1 and {self.width} (inclusive)")
        if size_min > size_max:
            raise ValueError("size_min must be less than or equal to size_max")

        if not (0 <= lossy_min <= 200):
            raise ValueError(f"lossy_min must be between {self.LOSSY_MIN} and {self.LOSSY_MAX} (inclusive)")
        if not (0 <= lossy_max <= 200):
            raise ValueError(f"lossy_max must be between {self.LOSSY_MIN} and {self.LOSSY_MAX} (inclusive)")
        if lossy_min > lossy_max:
            raise ValueError("lossy_min must be less than or equal to lossy_max")

        if fps_max < self.fps or size_max < self.width:
            self._create_intermediate(fps_max, size_max)

        self._create_palette()

        vs = values(
            MinMax(fps_min, fps_max),
            MinMax(size_min, size_max),
            MinMax(lossy_min, lossy_max),
        )

        try:
            v = next(vs)
            while True:
                fps, size, lossy = v.fps, v.size, v.lossy
                print(f"generating a gif with options {fps=} {size=} {lossy=}")
                _, size = self._to_gif(fps, size, lossy)
                print(f"generated files size is {size} bytes", file=sys.stderr)

                if size > output_size_limit:
                    print(
                        "generated file was larger than the max size", file=sys.stderr
                    )
                    v = vs.send(False)
                else:
                    print(
                        "generated file was smaller than the max size", file=sys.stderr
                    )
                    v = vs.send(True)

        except StopIteration as v:
            best = v.value

            fps, size, lossy = best.fps, best.size, best.lossy
            print(
                f"best options found were {fps=} {size=} {lossy=}",
                file=sys.stderr,
            )
            p = self.tmp / self._file_name(fps, size, lossy)
            p.rename(output_file)

            return 0

        except UnsatisfiableConstraints:
            print("no options could generate a small enough gif", file=sys.stderr)
            return 1
