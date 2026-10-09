#!/usr/bin/env python3
"""Dev-set diagnosis for the improvement loop (PLAN.md): for each removed reference,
is it in the sweep's candidate pool at all (a retrieval problem if not), and at what
rank (a ranking problem if low)? Which discovery paths reached it?

Runs run-survey.py from a given skill directory on dev drafts, keeps the full
candidates.json, and reports pool recall, Recall@30/@100 and the paths of each hit.
Extra run-survey arguments after `--` are passed through, so variants compare directly.

  dev_diag.py --skill <dir> --drafts private/drafts --gold private/gold.json --tag base ids... [-- --flag]
"""
import argparse, json, os, pathlib, subprocess, sys, tempfile, time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from score import same_work  # noqa: E402


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    extra = []
    if "--" in argv:
        i = argv.index("--"); extra = argv[i + 1:]; argv = argv[:i]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skill", required=True); ap.add_argument("--drafts", required=True)
    ap.add_argument("--gold", required=True); ap.add_argument("--tag", required=True)
    ap.add_argument("--out", default="private/dev"); ap.add_argument("--disable", default="openalex")
    ap.add_argument("ids", nargs="+")
    a = ap.parse_args(argv)
    G = json.loads(pathlib.Path(a.gold).read_text())
    outdir = pathlib.Path(a.out) / a.tag; outdir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, SCHOLARLY_DISABLE=a.disable)
    rows = []
    for pid in a.ids:
        tmp = tempfile.mkdtemp(prefix=f"dev-{pid}-")
        t0 = time.time()
        p = subprocess.run([sys.executable, str(pathlib.Path(a.skill) / "assets" / "run-survey.py"),
                            str(pathlib.Path(a.drafts) / pid), "--out", tmp, "--quiet"] + extra,
                           capture_output=True, text=True, env=env, timeout=5400)
        try:
            cands = json.loads((pathlib.Path(tmp) / "candidates.json").read_text())
        except (OSError, ValueError):
            cands = []
        (outdir / f"{pid}.candidates.json").write_text(json.dumps(cands))
        me = G["self"][pid]
        cands = [c for c in cands if not same_work(c, me)]
        for r in G["gold"][pid]:
            rank = next((i + 1 for i, c in enumerate(cands) if same_work(c, r)), None)
            rows.append({"case": pid, "key": r["key"], "policy": r["policy"],
                         "memory": r["key"] in G.get("memory", {}).get(pid, []),
                         "rank": rank, "paths": cands[rank - 1].get("paths", []) if rank else [],
                         "grade": cands[rank - 1].get("grade") if rank else None})
        print(pid, "exit", p.returncode, "pool", len(cands), "secs", round(time.time() - t0),
              "fail:", (p.stderr.strip().splitlines() or [""])[-1][:120], flush=True)
    (outdir / "rows.json").write_text(json.dumps(rows, indent=1))
    def rate(sel, k=None):
        s = [r for r in rows if sel(r)]
        hit = [r for r in s if r["rank"] and (k is None or r["rank"] <= k)]
        return f"{len(hit)}/{len(s)}"
    for name, sel in (("all", lambda r: True), ("key", lambda r: r["policy"] == "key"),
                      ("nonmemory", lambda r: not r["memory"]),
                      ("key-nonmemory", lambda r: r["policy"] == "key" and not r["memory"])):
        print(f"{a.tag:>10} {name:>14}: pool {rate(sel)}  @100 {rate(sel, 100)}  @30 {rate(sel, 30)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
