import tempfile
import re
import typing as t
import secrets
import sys
from pathlib import Path
from math import ceil

import optuna

from .cmd import cmd


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
        self.fps = int(fps[1]) / int(fps[2])

        width = width_re.search(stdout)
        if width is None:
            raise ValueError("could not get width of the video")
        self.width = int(width[1])

        height = height_re.search(stdout)
        if height is None:
            raise ValueError("could not get height of the video")
        self.height = int(height[1])

    def _temp_file(self) -> Path:
        return self.tmp / f"{secrets.token_urlsafe()}.gif"

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
            "-y",
            "-i",
            self.video_file,
            "-vf",
            f"fps={fps},scale={size}:-1:flags=lanczos",
            output_file,
            check=True,
        )

    def _to_gif_ffmpeg(self, fps: int, size: int) -> Path:
        input_file = self.video_file
        if self.intermediate.exists():
            input_file = self.intermediate

        output_file = self.tmp / self._file_name(fps, size)
        if output_file.exists():
            return output_file

        output_file_tmp = self._temp_file()

        # TODO better error handling
        cmd(
            "ffmpeg",
            "-y",
            "-i",
            input_file,
            "-i",
            self.palette,
            "-lavfi",
            f"fps={fps:.2f},scale={size}:-1:flags=lanczos,paletteuse",
            "-loop",
            "0",
            output_file_tmp,
            check=True,
        )

        output_file_tmp.rename(output_file)
        return output_file

    def _to_gif(self, fps: int, size: int, lossy: int) -> t.Tuple[Path, int]:
        created_file = self._to_gif_ffmpeg(fps, size)

        output_file = self.tmp / self._file_name(fps, size, lossy)
        if output_file.exists():
            return output_file, output_file.stat().st_size

        output_file_tmp = self._temp_file()

        # TODO better error handling
        cmd(
            "gifsicle",
            "-O3",
            f"--lossy={lossy}",
            created_file,
            "-o",
            output_file_tmp,
            check=True,
        )

        output_file_tmp.rename(output_file)
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
        trials: t.Optional[int],
        timeout: t.Optional[int],
        jobs: int,
    ) -> int:
        if output_size_limit <= 0:
            raise ValueError("output_size_limit must be larger than zero")

        if not (0 < fps_min <= self.fps):
            raise ValueError(f"fps_min must be larger than 0 and at most {self.fps}")
        if not (0 < fps_max <= self.fps):
            raise ValueError(f"fps_max must be larger than 0 and at most {self.fps}")
        if fps_min > fps_max:
            raise ValueError("fps_min must be less than or equal to fps_max")

        if not (1 <= size_min <= self.width):
            raise ValueError(f"size_min must be between 1 and {self.width} (inclusive)")
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

        print(
            "trying to find the optimal values for the follwing parameters within these ranges",
            f"fps   = {fps_min:>5.2f} .. {fps_max:<5.2f}",
            f"size  = {size_min:>5} .. {size_max:<5}",
            f"lossy = {lossy_min:>5} .. {lossy_max:<5}",
            sep="\n\t"
        )

        if fps_max < self.fps or size_max < self.width:
            self._create_intermediate(fps_max, size_max)

        self._create_palette()

        def objective(trial: optuna.Trial) -> float:
            fps = trial.suggest_float("fps", fps_min, fps_max)
            size = trial.suggest_int("size", size_min, size_max, log=True)
            lossy = trial.suggest_int("lossy", lossy_min, lossy_max)

            _, size = self._to_gif(fps, size, lossy)
            if size > output_size_limit:
                return output_size_limit + (size - output_size_limit) ** 2

            # fps should affect file size linearly
            dist_fps = delta(fps_min, fps_max, fps)

            # image size should affect file size exponentially
            dist_size = delta(size_min, size_max, size)
            dist_size **= 0.75

            # compression is likely to affect file size logarithmically
            dist_lossy = 1.0 - delta(lossy_min, lossy_max, lossy)
            dist_lossy **= 2.5

            dist = dist_fps + dist_size + dist_lossy

            if dist == 0:
                return float("inf")

            return (1 + output_size_limit - size) / dist

        study = optuna.create_study()

        try:
            print(f"starting optimization with {trials=} {timeout=} {jobs=}")
            study.optimize(objective, n_trials=trials, timeout=timeout, n_jobs=jobs)
        except KeyboardInterrupt:
            print("user stopped optimization")

        best = study.best_params
        fps, size, lossy = best["fps"], best["size"], best["lossy"]
        print(f"best results came with {fps=:.2f} {size=} {lossy=}")

        best_gif = self.tmp / self._file_name(fps, size, lossy)
        if best_gif.stat().st_size > output_size_limit:
            print("best generated gif is larger than the output size limit")
        best_gif.rename(output_file)

        return 0


def delta(min: int, max: int, x: int) -> float:
    div = abs(min - max)
    if div == 0:
        return 1.0
    return abs(min - x) / div
