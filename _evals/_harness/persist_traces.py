#!/usr/bin/env python3
"""Copy every run's trace out of /private/tmp into a durable directory and point the result JSON at it.

`claude plugin eval --keep-temp` leaves traces in /private/tmp/e-XXXX/out/trace.jsonl, which macOS deletes
after about three days and Time Machine does not back up. B5's first 76 runs were lost that way
(2026-11-18). Run this right after each eval call:

  persist_traces.py out/b5/clean/CASE.json out/b5/traces

Exits non-zero, and changes nothing, if any trace is already gone.
"""
import json, pathlib, shutil, sys


def main(result_json, dest):
    rj = pathlib.Path(result_json)
    data = json.loads(rj.read_text())
    dest = pathlib.Path(dest).resolve()
    plan = []
    for case in data["cases"]:
        name = case["dir"].rstrip("/").split("/")[-1]
        for arm, runs in case["arms"].items():
            for i, r in enumerate(runs):
                src = pathlib.Path(r.get("tracePath") or "")
                tgt = dest / name / f"{arm}-{i}.jsonl"
                if src == tgt and tgt.is_file():
                    continue
                if not src.is_file():
                    sys.exit(f"persist_traces.py: {name} {arm}[{i}] trace missing: {src}")
                plan.append((r, src, tgt))
    for r, src, tgt in plan:
        tgt.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, tgt)
        r["tracePath"] = str(tgt)
    rj.write_text(json.dumps(data, indent=2))
    print(f"persisted {len(plan)} traces from {rj.name}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
