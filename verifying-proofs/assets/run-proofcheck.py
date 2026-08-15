#!/usr/bin/env python3
"""Runner so proofcheck works from any directory.

`python3 -m proofcheck` only resolves when the package's parent directory is on
sys.path, which it is not when you are sitting in a paper directory. Invoke this
by absolute path instead:

    python3 ~/.claude/skills/verifying-proofs/assets/run-proofcheck.py main.tex \
        --out review-assets/
"""
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, os.path.expanduser("~/.claude/skills/_shared"))

from proofcheck.__main__ import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
