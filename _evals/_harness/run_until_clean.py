#!/usr/bin/env python3
"""Run a claude-plugin-eval suite case by case batch, redoing every case that lost a run
to an account or session limit, until no case is affected.

Rule (protocols A and B): a run that ends on a usage limit is unobserved, so every run
of an affected case is redone in every arm. Complete cases are written once to
<out>/clean/<case>.json and never rerun. When the limit message says when it resets
("resets 7am"), the driver sleeps until then plus a margin.

  run_until_clean.py --plugin <dir> --cases-from <dir with all case folders> --out <dir> \
      --ablation with-without -- <extra claude plugin eval args>
"""
import argparse, datetime, json, os, pathlib, re, shutil, subprocess, sys, time

LIMIT = re.compile(r"(session|usage) limit", re.I)
RESET = re.compile(r"resets (\d{1,2})(?::(\d{2}))?\s*(am|pm)", re.I)


def reset_wait(messages, margin=300):
    for m in messages:
        r = RESET.search(m)
        if r:
            h = int(r.group(1)) % 12 + (12 if r.group(3).lower() == "pm" else 0)
            now = datetime.datetime.now()
            t = now.replace(hour=h, minute=int(r.group(2) or 0), second=0, microsecond=0)
            if t <= now:
                t += datetime.timedelta(days=1)
            return (t - now).total_seconds() + margin
    return 1800


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    extra = argv[argv.index("--") + 1:] if "--" in argv else []
    argv = argv[:argv.index("--")] if "--" in argv else argv
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plugin", required=True); ap.add_argument("--cases-from", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--ablation", default="with-without")
    ap.add_argument("--max-rounds", type=int, default=6)
    a = ap.parse_args(argv)
    out = pathlib.Path(a.out); (out / "clean").mkdir(parents=True, exist_ok=True)
    allcases = sorted(p.name for p in pathlib.Path(a.cases_from).iterdir() if p.is_dir())
    evals = pathlib.Path(a.plugin) / "evals"
    for rnd in range(1, a.max_rounds + 1):
        pending = [c for c in allcases if not (out / "clean" / f"{c}.json").exists()]
        print(f"round {rnd}: {len(pending)} pending", flush=True)
        if not pending:
            return 0
        if evals.exists():
            shutil.rmtree(evals)
        evals.mkdir(parents=True)
        for c in pending:
            shutil.copytree(pathlib.Path(a.cases_from) / c, evals / c)
        res = out / f"round{rnd}.json"
        cmd = ["claude", "plugin", "eval", a.plugin, "--ablation", a.ablation, "--json", str(res)] + extra
        with open(out / f"round{rnd}.log", "w") as log:
            subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
        try:
            d = json.loads(res.read_text())
        except (OSError, ValueError):
            print("no result file; waiting 30 min", flush=True); time.sleep(1800); continue
        limit_msgs = []
        for case in d["cases"]:
            name = case["dir"].rstrip("/").split("/")[-1]
            errs = [str(r.get("error")) for runs in case["arms"].values() for r in runs if r.get("error")]
            hit = [e for e in errs if LIMIT.search(e)]
            if hit:
                limit_msgs += hit
                continue
            (out / "clean" / f"{name}.json").write_text(json.dumps({**d, "cases": [case]}))
        if limit_msgs:
            w = reset_wait(limit_msgs)
            print(f"round {rnd}: {len(limit_msgs)} runs hit a usage limit; sleeping {w/60:.0f} min", flush=True)
            time.sleep(w)
    return 1


if __name__ == "__main__":
    sys.exit(main())
