# Usage: consistency.py <protocol scorer.py> RUNS.jsonl[.gz] ... (run from the scorer's folder)
"""Run-to-run consistency of issue lists: same case, same arm, pairs of runs.
Two issues match when their located draft spans are within 3 lines. Agreement of a pair =
(matched issues in A + matched issues in B) / (|A| + |B|), over located issues only."""
import json, sys, itertools, statistics as st, collections, importlib.util, pathlib
scorer, files = sys.argv[1], sys.argv[2:]
spec = importlib.util.spec_from_file_location("sc", scorer); sc = importlib.util.module_from_spec(spec); spec.loader.exec_module(sc)
runs = collections.defaultdict(list)
for r in sc.read(files):
    runs[(r["arm"], r["case"])].append(r)
def spans(r, case):
    c = sc.load_case(case)
    return [loc for k, f, loc, on in sc.located(c, r.get("final")) if loc], [on for *_, on in sc.located(c, r.get("final"))]
def near(a, b): return a[0] - 3 <= b[1] and b[0] - 3 <= a[1]
res = collections.defaultdict(lambda: {"agree": [], "n": [], "cv": [], "hit_split": 0, "cases": 0})
for (arm, case), rs in sorted(runs.items()):
    L = [spans(r, case)[0] for r in rs]
    ns = [len(x) for x in L]
    R = res[arm]; R["cases"] += 1; R["n"] += ns
    if len(ns) > 1 and st.mean(ns): R["cv"].append(st.pstdev(ns) / st.mean(ns))
    for a, b in itertools.combinations(L, 2):
        if not a and not b: continue
        ma = sum(any(near(x, y) for y in b) for x in a); mb = sum(any(near(y, x) for x in a) for y in b)
        R["agree"].append((ma + mb) / (len(a) + len(b)))
for arm, R in sorted(res.items()):
    print(f"{arm:8s} cases {R['cases']:2d}  issues/run {st.mean(R['n']):5.1f} (range {min(R['n'])}-{max(R['n'])})  "
          f"count CV {(st.mean(R["cv"]) if R["cv"] else float("nan")):.2f}  pairwise agreement {(st.mean(R["agree"]) if R["agree"] else float("nan")):.2f} (n pairs {len(R['agree'])})")
