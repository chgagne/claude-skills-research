"""Compatibility alias: the retrieval layer lives in _shared/scholarly.

This module *becomes* scholarly.retrieval rather than re-exporting its names.
Re-exporting would bind copies, so a test that patches `sources._raw_get` would
leave `get_bytes` calling the original — the tests would keep passing while
testing nothing. Aliasing the module object keeps patching transparent.
"""
import os
import sys

_SHARED = os.path.expanduser("~/.claude/skills/_shared")
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

from scholarly import retrieval as _retrieval  # noqa: E402

sys.modules[__name__] = _retrieval
