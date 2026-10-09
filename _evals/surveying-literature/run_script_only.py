#!/usr/bin/env python3
"""Script-only arm: run-survey.py on each draft, no agent, its own ranking.

Writes one JSONL row per paper in the shape score.py reads, the top 30 candidates of
candidates.json (already sorted by grade, then score) as the final answer. Engines are
switched off with SCHOLARLY_DISABLE exactly as in the agent arms. Runs outside the eval
sandbox, with the user's environment, so the S2 key and network are available.

  run_script_only.py --drafts private/drafts --skill <frozen skill dir> --out runs/script.jsonl ids...
"""
import argparse, json, os, pathlib, subprocess, sys, tempfile, time


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--drafts", required=True); ap.add_argument("--skill", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--disable", default="openalex")
    ap.add_argument("ids", nargs="+")
    a = ap.parse_args(argv)
    env = dict(os.environ, SCHOLARLY_DISABLE=a.disable)
    runner = pathlib.Path(a.skill) / "assets" / "run-survey.py"
    with open(a.out, "a") as out:
        for pid in a.ids:
            tmp = tempfile.mkdtemp(prefix=f"sweep-{pid}-")
            t0 = time.time()
            p = subprocess.run([sys.executable, str(runner), str(pathlib.Path(a.drafts) / pid), "--out", tmp, "--quiet"],
                               capture_output=True, text=True, env=env, timeout=3600)
            cands = []
            try:
                cands = json.loads((pathlib.Path(tmp) / "candidates.json").read_text())
            except (OSError, ValueError):
                pass
            top = [{"title": c.get("title"), "year": c.get("year"), "doi": c.get("doi"),
                    "first_author": (c.get("authors") or [None])[0], "grade": c.get("grade")} for c in cands[:30]]
            final = "```json\n" + json.dumps({"candidates": top}) + "\n```"
            out.write(json.dumps({"arm": "script", "case": pid, "run": 0, "final": final,
                                  "trace": p.stderr, "exit": p.returncode, "n_candidates": len(cands),
                                  "seconds": round(time.time() - t0)}) + "\n")
            out.flush()
            print(pid, "exit", p.returncode, "candidates", len(cands), "seconds", round(time.time() - t0), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
