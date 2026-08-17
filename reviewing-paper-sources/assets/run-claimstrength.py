#!/usr/bin/env python3
"""Runner so the check works from any directory.

`python3 -m claimstrength` only resolves when this directory is on sys.path,
which it is not when you are sitting in a paper directory. Invoke by absolute
path:

    python3 ~/.claude/skills/reviewing-paper-sources/assets/run-claimstrength.py . \
        --out review-assets/
"""
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(pathlib.Path.home() / ".claude" / "skills" / "_shared"))

from claimstrength.__main__ import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
