"""Compatibility alias: text normalisation lives in _shared/scholarly.textnorm.

Aliased rather than re-exported for the same reason as sources.py — see that
module's docstring.
"""
import os
import sys

_SHARED = os.path.expanduser("~/.claude/skills/_shared")
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

from scholarly import textnorm as _textnorm  # noqa: E402

sys.modules[__name__] = _textnorm
