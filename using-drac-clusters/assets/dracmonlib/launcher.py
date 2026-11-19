"""`dracmon install-launcher`: put a small `dracmon` command on the user's PATH.

The launcher is a POSIX sh script (macOS and Linux) that runs this skill's
dracmon.py through uv and passes every argument through. It never edits shell
configuration: when the target directory is not on PATH it prints the line to add.
"""
from __future__ import annotations

import os
from pathlib import Path

ENTRY = Path(__file__).resolve().parent.parent / "dracmon.py"
DEFAULT_DIR = Path("~/bin")


def _sh_quote(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"


def render(entry: Path = ENTRY) -> str:
    return f"""#!/bin/sh
# dracmon: terminal monitor for DRAC clusters (using-drac-clusters skill).
# Written by `dracmon install-launcher`; every argument is passed through:
#   dracmon                   dashboard
#   dracmon doctor            check the ssh setup
#   dracmon service install   background collector
script={_sh_quote(str(entry))}
uv=$(command -v uv) || {{ echo "dracmon: uv not found (https://docs.astral.sh/uv/)" >&2; exit 1; }}
[ -f "$script" ] || {{ echo "dracmon: $script not found (skill moved? rerun install-launcher)" >&2; exit 1; }}
exec "$uv" run --quiet --script "$script" "$@"
"""


def _on_path(directory: Path, path_env: str) -> bool:
    target = directory.resolve()
    for p in path_env.split(os.pathsep):
        if p and Path(p).expanduser().resolve() == target:
            return True
    return False


def install(directory: Path = DEFAULT_DIR, *, path_env: str | None = None,
            force: bool = False) -> tuple[int, str]:
    """Write ``<directory>/dracmon``. Returns (exit code, message for the user)."""
    directory = Path(directory).expanduser()
    target = directory / "dracmon"
    text = render()
    if target.exists() and not force:
        try:
            same = target.read_text() == text
        except OSError:
            same = False
        if not same:
            return 1, (f"{target} exists and differs; not touched. "
                       f"Use --force to replace it.")
    directory.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(".dracmon.tmp")
    tmp.write_text(text)
    tmp.chmod(0o755)
    tmp.replace(target)
    path_env = os.environ.get("PATH", "") if path_env is None else path_env
    lines = [f"wrote {target}"]
    if _on_path(directory, path_env):
        lines.append("run: dracmon")
    else:
        lines += [f"{directory} is not on your PATH. Add this line to ~/.zshrc or ~/.bashrc,",
                  "then open a new terminal:",
                  f'  export PATH="{directory}:$PATH"']
    return 0, "\n".join(lines)
