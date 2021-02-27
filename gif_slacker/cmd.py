import subprocess
import typing as t
import os
from shlex import join


def cmd(*args: t.List[t.Any], check=False) -> t.Tuple[int, str, str]:
    params = list(map(str, args))
    if os.environ.get("DEBUG", "") not in ("0", ""):
        print(f"[cmd] {join(params)}")
    out = subprocess.run(params, capture_output=True, check=check)
    return (out.returncode, out.stdout, out.stderr)
