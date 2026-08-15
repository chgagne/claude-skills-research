#!/usr/bin/env python3
"""Runner so explain works from any directory.

`python3 -m explain` only resolves when the package's parent directory is on
sys.path, which it is not when you are sitting in a paper directory. Invoke this
by absolute path instead:

    python3 ~/.claude/skills/explaining-derivations/assets/run-explain.py main.tex \
        --out derivations/ --level grad-ml --plan-only
"""
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, os.path.expanduser("~/.claude/skills/_shared"))

from explain.__main__ import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
