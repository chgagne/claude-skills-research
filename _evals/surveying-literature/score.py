#!/usr/bin/env python3
"""Score surveying-literature runs: recovery of held-out references. See PLAN.md.

Input: run JSONL (from _harness/extract.py, or one row per probe file) with "arm", "case"
(the arXiv id of the source paper), "run" and "final" (the last message, ending in a
```json {"candidates": [...]}``` block). Gold: {"gold": {case: [removed refs]},
"cited_all": {case: [every reference of the original paper]}, "memory": {case: [keys]},
"self": {case: {"title", "arxiv"}} (the source paper, never scored).
Stdlib only.
"""
import argparse, difflib, json, os, pathlib, re, sys
from collections import defaultdict

sys.path.insert(0, os.path.expanduser("~/.claude/skills/_shared"))
from scholarly.textnorm import norm_title  # noqa: E402

_BLOCK = re.compile(r"```json\s*(.*?)```", re.S)
_ARXIV = re.compile(r"(\d{4}\.\d{4,5})")


def candidates(final):
    """Ranked candidate list from the last parseable json block, or None."""
    for raw in reversed(_BLOCK.findall(final or "")):
        try:
            c = json.loads(raw).get("candidates")
            if isinstance(c, list):
                return [x for x in c if isinstance(x, dict) and x.get("title")]
        except (ValueError, AttributeError):
            continue
    return None


def _ids(x):
    doi = (x.get("doi") or "").lower().replace("https://doi.org/", "").strip() or None
    m = _ARXIV.search(str(x.get("arxiv") or "") or (doi or ""))
    return doi, (m.group(1) if m else None)


def same_work(cand, ref):
    """DOI or arXiv id agree, or titles match: equal, one a 6+-word prefix of the
    other (subtitles), or difflib ratio >= 0.88 (memory garbles titles slightly)."""
    cd, ca = _ids(cand)
    rd, ra = _ids(ref)
    if (cd and rd and cd == rd) or (ca and ra and ca == ra):
        return True
    a, b = norm_title(cand.get("title", "")), norm_title(ref.get("title", ""))
    if not a or not b:
        return False
    if a == b:
        return True
    wa, wb = a.split(), b.split()
    n = min(len(wa), len(wb))
    if n >= 6 and wa[:n] == wb[:n]:
        return True
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.88


def score_run(cands, removed, cited_all, self_ref=None):
    """Per-run hits. The source paper itself is dropped from the list before ranking."""
    if cands is None:
        return None
    if self_ref:
        cands = [c for c in cands if not same_work(c, self_ref)]
    cands = cands[:30]
    out = {"hits": {}, "n": len(cands)}
    for r in removed:
        rank = next((i + 1 for i, c in enumerate(cands) if same_work(c, r)), None)
        out["hits"][r["key"]] = rank
    kept = [x for x in cited_all if x["key"] not in {r["key"] for r in removed}]
    out["already_cited"] = sum(any(same_work(c, k) for k in kept) for c in cands)
    out["cited_by_paper"] = sum(any(same_work(c, k) for k in cited_all) for c in cands)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--gold", required=True)
    ap.add_argument("--cases", help="comma-separated subset (e.g. the test split)")
    a = ap.parse_args(argv)
    G = json.loads(pathlib.Path(a.gold).read_text())
    keep = set(a.cases.split(",")) if a.cases else None
    memory = {c: set(v) for c, v in G.get("memory", {}).items()}
    agg = defaultdict(lambda: defaultdict(lambda: [0, 0]))   # arm -> bucket -> [hits, total]
    fails = defaultdict(int); per = []
    for path in a.runs:
        for line in pathlib.Path(path).read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if keep and r["case"] not in keep:
                continue
            s = score_run(candidates(r.get("final")), G["gold"][r["case"]], G["cited_all"][r["case"]],
                          G.get("self", {}).get(r["case"]))
            if s is None:
                fails[r["arm"]] += 1
                s = {"hits": {x["key"]: None for x in G["gold"][r["case"]]}, "n": 0,
                     "already_cited": 0, "cited_by_paper": 0}
            per.append({"arm": r["arm"], "case": r["case"], "run": r.get("run"), **s})
            for ref in G["gold"][r["case"]]:
                rank = s["hits"][ref["key"]]
                mem = "memory" if ref["key"] in memory.get(r["case"], set()) else "nonmemory"
                for k in (10, 30):
                    for bucket in (f"{ref['policy']}@{k}", f"{ref['policy']}/{mem}@{k}", f"all@{k}"):
                        agg[r["arm"]][bucket][1] += 1
                        agg[r["arm"]][bucket][0] += int(rank is not None and rank <= k)
    out = {arm: {"format_failures": fails[arm],
                 **{b: round(h / t, 3) for b, (h, t) in sorted(v.items())},
                 "n_per_bucket": {b: t for b, (h, t) in sorted(v.items())}}
           for arm, v in agg.items()}
    print(json.dumps({"summary": out, "runs": per}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
