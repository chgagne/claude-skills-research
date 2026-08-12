#!/usr/bin/env python3
"""Runner so bibcheck works from any directory.

`python3 -m bibcheck` only resolves when the package's parent directory is on
sys.path, which it is not when you are sitting in a paper directory. Invoke this
by absolute path instead:

    python3 ~/.claude/skills/verifying-bibliography/assets/run-bibcheck.py \
        refs.bib --bbl main.bbl --out review-assets/
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from bibcheck.__main__ import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
