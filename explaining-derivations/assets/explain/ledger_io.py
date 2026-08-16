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

    A JSON object that is not keyed by step id is refused rather than accepted
    as an empty mapping. `proof-ledger.json` is the obvious wrong file to reach
    for — it sits next to `proofsteps.csv` in the same `review-assets/` and is
    the one people name — and silently accepting it produces a whole document of
    *not run* cells that looks exactly like a run where no engine fired.
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
    if data and not any(str(k).startswith("proof/") for k in data):
        raise ValueError(
            "%s carries no per-step verdicts: its keys are %s, not step ids like "
            "'proof/<label>/s07'. verifying-proofs writes the verdicts to "
            "proofsteps.csv; proof-ledger.json is the step ledger, not the result."
            % (os.path.basename(path), ", ".join(sorted(map(str, data))[:4])))
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
