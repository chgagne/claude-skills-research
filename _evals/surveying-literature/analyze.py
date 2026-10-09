#!/usr/bin/env python3
"""Apply a protocol's analysis to finished runs (PROTOCOL-A.md): contamination, scoring,
the success criterion, an exact McNemar test, and per-run covariates.

  analyze.py --gold private/gold.json --split test runs/*.jsonl
"""
import argparse, json, math, pathlib, re, sys
from collections import defaultdict

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import score as S          # noqa: E402
import contamination as C  # noqa: E402

PRIMARY = "key/nonmemory@30"


def mcnemar_exact(b, c):
    """Two-sided exact McNemar p on b (only A) and c (only B) discordant pairs."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return min(1.0, 2 * p)


def degraded(trace):
    """Source failures the sweep printed in this run (0 when it never ran)."""
    # the warning is echoed more than once in a trace (tool result, then quoted);
    # take the largest single report, not the sum
    n = 0
    for m in re.finditer(r"source coverage was degraded[^\n]*?((?:[\w.]+ \(\d+\)(?:, )?)+)", trace or ""):
        n = max(n, sum(int(x) for x in re.findall(r"\((\d+)\)", m.group(1))))
    return n


def sweep_ran(trace):
    return bool(re.search(r"wrote [^\n]*candidates\.json", trace or ""))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("runs", nargs="+"); ap.add_argument("--gold", required=True)
    ap.add_argument("--split", default="test"); ap.add_argument("--json-out")
    a = ap.parse_args(argv)
    G = json.loads(pathlib.Path(a.gold).read_text())
    cases = set(G["split"][a.split])
    memory = {c: set(v) for c, v in G.get("memory", {}).items()}
    rows, discarded = [], []
    for path in a.runs:
        for line in pathlib.Path(path).read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r["case"] not in cases:
                continue
            me = G["self"][r["case"]]
            f = C.flags(r.get("trace"), me.get("arxiv"), me.get("doi"), me.get("title", ""))
            if f:
                discarded.append({"arm": r["arm"], "case": r["case"], "run": r.get("run"), "flags": f})
                continue
            rows.append(r)
    per_arm = defaultdict(list)
    for r in rows:
        s = S.score_run(S.candidates(r.get("final")), G["gold"][r["case"]], G["cited_all"][r["case"]], G["self"][r["case"]])
        per_arm[r["arm"]].append({"case": r["case"], "run": r.get("run"), "s": s,
                                  "degraded": degraded(r.get("trace")), "sweep_ran": sweep_ran(r.get("trace")),
                                  "cost": r.get("cost_usd"), "seconds": r.get("seconds"), "turns": r.get("turns")})

    def bucket(ref, case):
        return ("key" if ref["policy"] == "key" else "random"), \
               ("memory" if ref["key"] in memory.get(case, set()) else "nonmemory")

    summary = {}
    hits = defaultdict(dict)       # arm -> (case, run, refkey) -> bool, for McNemar
    for arm, rs in per_arm.items():
        agg = defaultdict(lambda: [0, 0])
        already = n = 0
        for x in rs:
            s = x["s"]
            for ref in G["gold"][x["case"]]:
                rank = s["hits"][ref["key"]] if s else None
                pol, mem = bucket(ref, x["case"])
                for k in (10, 30):
                    for b in (f"{pol}/{mem}@{k}", f"{pol}@{k}", f"all@{k}"):
                        agg[b][1] += 1; agg[b][0] += int(rank is not None and rank <= k)
                hits[arm][(x["case"], x["run"], ref["key"])] = rank is not None and rank <= 30 and pol == "key" and mem == "nonmemory"
            if s:
                already += s["already_cited"]; n += s["n"]
        summary[arm] = {"runs": len(rs), "format_failures": sum(1 for x in rs if not x["s"]),
                        **{b: round(h / t, 3) for b, (h, t) in sorted(agg.items())},
                        "n_primary": agg[PRIMARY][1], "already_cited_rate": round(already / n, 3) if n else None,
                        "sweep_ran": sum(x["sweep_ran"] for x in rs),
                        "degraded_mean": round(sum(x["degraded"] for x in rs) / len(rs), 2) if rs else None,
                        "cost_mean": round(sum(x["cost"] or 0 for x in rs) / len(rs), 3) if rs else None,
                        "seconds_mean": round(sum(x["seconds"] or 0 for x in rs) / len(rs)) if rs else None}

    verdict = {}
    if "skill" in summary and "without" in summary:
        gap = summary["skill"][PRIMARY] - summary["without"][PRIMARY]
        fp_ok = (summary["skill"]["already_cited_rate"] or 0) <= (summary["without"]["already_cited_rate"] or 0)
        # pair on (case, run index, reference); runs are matched by index within a case
        keys = [k for k in hits["skill"] if k in hits["without"]]
        b = sum(1 for k in keys if hits["skill"][k] and not hits["without"][k])
        c = sum(1 for k in keys if hits["without"][k] and not hits["skill"][k])
        verdict = {"primary_gap_points": round(100 * gap, 1), "criterion_1": gap >= 0.15,
                   "criterion_2": fp_ok, "success": gap >= 0.15 and fp_ok,
                   "mcnemar_pairs": len(keys), "only_skill": b, "only_without": c,
                   "mcnemar_p": round(mcnemar_exact(b, c), 4)}
        if "self" in summary:
            verdict["gap_vs_self_points"] = round(100 * (summary["skill"][PRIMARY] - summary["self"][PRIMARY]), 1)
    out = {"split": a.split, "discarded": discarded, "summary": summary, "verdict": verdict}
    print(json.dumps(out, indent=1))
    if a.json_out:
        pathlib.Path(a.json_out).write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
