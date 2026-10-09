#!/usr/bin/env python3
"""Turn `claude plugin eval --json` results into the run JSONL that score.py reads.

Needs the run traces, so the eval must be run with --keep-temp. Each run's arm is the
eval arm ("with"/"without") renamed with --with-name, so two eval calls can be pooled:

  extract.py skill.json --with-name skill > skill.jsonl
  extract.py self.json  --with-name self  > self.jsonl
"""
import argparse, json, pathlib, sys


def final_and_trace(trace_path):
    p = pathlib.Path(trace_path or "")
    if not p.is_file():
        return None, ""
    text = p.read_text(encoding="utf-8", errors="replace")
    final = None
    for line in text.splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("type") == "result":
            final = ev.get("result")
    return final, text


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("result_json")
    ap.add_argument("--with-name", required=True)
    a = ap.parse_args(argv)
    data = json.loads(pathlib.Path(a.result_json).read_text())
    for case in data["cases"]:
        name = case["dir"].rstrip("/").split("/")[-1]          # evals/case1 -> case1
        for arm, runs in case["arms"].items():
            for i, r in enumerate(runs):
                final, trace = final_and_trace(r.get("tracePath"))
                print(json.dumps({"arm": a.with_name if arm == "with" else "without", "case": name, "run": i,
                                  "final": final, "trace": trace, "error": r.get("error"),
                                  "cost_usd": r.get("costUsd"), "seconds": r.get("durationSeconds"),
                                  "turns": r.get("turns")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
