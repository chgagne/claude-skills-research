"""Compatibility alias: BibTeX parsing lives in _shared/scholarly.bibtex."""
import os
import sys

_SHARED = os.path.expanduser("~/.claude/skills/_shared")
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

from scholarly import bibtex as _bibtex  # noqa: E402

sys.modules[__name__] = _bibtex
