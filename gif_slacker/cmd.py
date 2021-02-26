import subprocess
import typing as t


def cmd(*args: t.List[t.Any], check=False) -> t.Tuple[int, str, str]:
    out = subprocess.run(list(map(str, args)), capture_output=True, check=check)
    return (out.returncode, out.stdout, out.stderr)
