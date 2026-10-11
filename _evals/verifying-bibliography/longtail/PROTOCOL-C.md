# verifying-bibliography: long-tail evaluation with the tools working (protocol C)

Written 2026-10-10, before any protocol-C run. Protocol `PROTOCOL.md` (here) and its results
measured the skills' instructions only: inside `claude plugin eval` neither skill's script could
run (no `_shared` in the run's HOME, no network for Bash). This protocol repeats the comparison
with the tools working. A smoke run (lt1, skill arm, 1 run, not scored) confirmed that
`run-bibcheck.py` now completes and reaches its sources.

## Material

The six frozen long-tail bibliographies (`cases/`), the same prompts, the published `gold.json`
(17 defects, 41 correct entries). Contamination: a trace mentioning `gold.json` or `_evals`
is discarded (the labels are public since cd7a594).

## Arms

- **without**: no skill.
- **skill**: `verifying-bibliography` at ee2fbc2, which now includes the DBLP SPARQL repair and
  the subtitle-aware preprint rule (both made after the first long-tail run).
- **self**: the frozen self-written skill (`../self-skill/`, sha256 unchanged).

Same model (`claude-opus-5-5`), tools, 60 turns, 25-minute timeout. Each run's scaffold installs
the frozen `_shared` and the S2 key file; Bash network is granted for api.crossref.org,
export.arxiv.org, sparql.dblp.org, api.semanticscholar.org, api.openalex.org, doi.org,
api.biorxiv.org and openlibrary.org in every arm.

**2 runs per case** (36 runs), not 3: the account owner capped evaluation use at 50% of the 5-hour
window and 80% of the 7-day window, and runs are launched case by case behind `usage_gate.py`.

## Scoring and criterion

`../score.py`, unchanged. Success, as in the first long-tail protocol: the skill's pooled recall
exceeds the without and self arms' by at least 20 points, and its false-positive rate is not
higher than either. Reported beside it: whether the script ran in each skill run, cost and time.
