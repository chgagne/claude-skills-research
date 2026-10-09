#!/usr/bin/env python3
"""Score verifying-bibliography eval runs against gold.json. See PROTOCOL.md.

Input: one JSONL file per arm, one object per run: {"arm", "case", "run", "final", "trace"}
where "final" is the agent's last message and "trace" any text to scan for contamination.
Stdlib only.
"""
import argparse, json, pathlib, re, sys
from collections import defaultdict

HERE = pathlib.Path(__file__).resolve().parent
LABELS = {"title", "authors", "doi", "metadata", "preprint", "nonexistent"}
_BLOCK = re.compile(r"```json\s*(.*?)```", re.S)


def flagged(final):
    """{key: label} from the last parseable json block, or None if there is none."""
    for raw in reversed(_BLOCK.findall(final or "")):
        try:
            data = json.loads(raw)
            return {f["key"]: f.get("problem") for f in data.get("flagged", [])}
        except (ValueError, TypeError, KeyError, AttributeError):
            continue
    return None


def score_run(gold_case, final):
    flags = flagged(final)
    bad = {k for k, v in gold_case.items() if v != "ok"}
    ok = set(gold_case) - bad
    if flags is None:
        return {"parsed": False, "tp": 0, "fp": 0, "n_bad": len(bad), "n_ok": len(ok), "label_ok": 0,
                "unknown": 0, "missed": sorted(bad), "false": []}
    keys = set(flags)
    tp = keys & bad
    return {"parsed": True, "tp": len(tp), "fp": len(keys & ok), "n_bad": len(bad), "n_ok": len(ok),
            "label_ok": sum(flags[k] == gold_case[k] for k in tp),
            "unknown": len(keys - set(gold_case)),
            "missed": sorted(bad - keys), "false": sorted(keys & ok)}


def contaminated(trace):
    return bool(re.search(r"gold\.json|_evals", trace or ""))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("runs", nargs="+", help="JSONL files of runs")
    ap.add_argument("--gold", default=str(HERE / "gold.json"))
    a = ap.parse_args(argv)
    gold = json.loads(pathlib.Path(a.gold).read_text())
    per_arm = defaultdict(list)
    for path in a.runs:
        for line in pathlib.Path(path).read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                if contaminated(r.get("trace")):
                    print(f"DISCARDED (contamination): {r['arm']} {r['case']} run {r['run']}")
                    continue
                s = score_run(gold[r["case"]], r.get("final"))
                per_arm[r["arm"]].append({**r, **s})
    out = {}
    for arm, rs in sorted(per_arm.items()):
        tp, nb = sum(r["tp"] for r in rs), sum(r["n_bad"] for r in rs)
        fp, no = sum(r["fp"] for r in rs), sum(r["n_ok"] for r in rs)
        caught = sum(r["tp"] for r in rs)
        out[arm] = {"runs": len(rs), "format_failures": sum(not r["parsed"] for r in rs),
                    "recall": tp / nb if nb else 0, "fp_rate": fp / no if no else 0,
                    "fp_entries": fp, "label_accuracy": sum(r["label_ok"] for r in rs) / caught if caught else 0,
                    "per_case_recall": {c: sum(r["tp"] for r in rs if r["case"] == c) /
                                        max(1, sum(r["n_bad"] for r in rs if r["case"] == c))
                                        for c in sorted({r["case"] for r in rs})}}
        missed = defaultdict(int); false = defaultdict(int)
        for r in rs:
            for k in r.get("missed", []): missed[f"{r['case']}:{k}"] += 1
            for k in r.get("false", []): false[f"{r['case']}:{k}"] += 1
        out[arm]["missed"] = dict(sorted(missed.items()))
        out[arm]["false_positives"] = dict(sorted(false.items()))
    print(json.dumps(out, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
