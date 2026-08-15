"""Ledger, verdicts and returned fragments, loaded from disk. Stdlib only."""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.expanduser("~/.claude/skills/_shared"))

from latexmath import ledger as _ledger  # noqa: E402


def build(main_tex, user_domains=None):
    return _ledger.build_ledger(main_tex, user_domains=user_domains)


def load_verdicts(path):
    """Per-step verdicts from `verifying-proofs`, as `{step_id: {...}}`.

    Accepts either `proofsteps.csv` or a JSON mapping. Absent, the result is
    empty — and then every *Checked* cell in every document reads *not run*,
    because the expander may not report a verdict it did not receive.
    """
    if not path:
        return {}
    if not os.path.exists(path):
        raise ValueError("no such verdicts file: %s" % path)
    if path.endswith(".csv"):
        out = {}
        with open(path, encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                sid = (row.get("step") or "").strip()
                sev = (row.get("severity") or "").strip()
                if sid and sev:
                    out[sid] = {"verdict": sev,
                                "engine": (row.get("engine") or "").strip() or None,
                                "script": (row.get("script") or "").strip() or None}
        return out
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict) and "verdicts" in data:
        data = data["verdicts"]
    if not isinstance(data, dict):
        raise ValueError("--verdicts must be a CSV or a JSON object keyed by step")
    return data


def load_fragments(path):
    """Returned `explain-fragment/1` objects: a directory of JSON, or one file."""
    if not path:
        return []
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, list) else [data]
    out = []
    for name in sorted(os.listdir(path)):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(path, name), encoding="utf-8") as fh:
            try:
                data = json.load(fh)
            except ValueError:
                continue
        out.extend(data if isinstance(data, list) else [data])
    return out
