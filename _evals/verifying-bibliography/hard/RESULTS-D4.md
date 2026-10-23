# Protocol D4 results: the reduced skill passes (2026-10-23)

Protocol: `PROTOCOL-D4.md` (81d1d4f), committed before the first run. 12 runs of the reduced skill
at 61ee681 on D's six cases, 14:44 to 15:24, $12.5 in model cost. No run failed, none timed out,
none was discarded.

| # | Criterion | D4 | Bar | D3 | D2 | Full skill (D) | Without (D) |
|---|---|---|---|---|---|---|---|
| 1 | Planted recall | 26/26 | at least 25/26 | 26/26 | 22/26 | 26/26 | 26/26 |
| 2 | False positives after adjudication | 11 | at most 22 | 17 | 17 | 15 | 15 |
| 3 | Natural-error recall | 128/146 = 0.88 | at least 0.80 | 0.90 | 0.89 | 0.83 | 0.74 |
| 4 | Script ran | 12 of 12 | at least 11 | 12 | 12 | 12 | - |
| 5 | Mean cost per run | $1.04 | at most $1.40 | $1.77 | $1.27 | $1.05 | $0.98 |

All columns use the final pool of 73 natural errors. D4 added no confirmed error; its one new
flag (`elhara2019coco` as a preprint) is a false positive: DBLP holds only the CoRR record.

**Verdict: all five criteria met. The reduction is merged** (SKILL.md 201 to 81 lines, the
removed text kept verbatim in `reference/design-notes.md`).

## What the three rounds showed

- D2: cutting the description of what the script compares lost the follow-up on title-only
  (`WEAK`) entries, where page errors hide: 4 planted defects missed in 2 runs.
- D3: restoring it as "look each one up" brought recall back but turned each lookup into a web
  search ($1.77 per run).
- D4: the same follow-up as one Bash pass over Crossref and a batched DBLP query kept recall at
  26/26, at the full skill's cost, with fewer false positives (WebSearch calls per run: 0 to 8,
  mean 1.6, against 23 to 25 in D3's long runs).

## Limits

The reduced text was revised twice on these same six bibliographies, so D4 shows it matches the
full skill here, not that it generalises better. On these cases neither version beats the bare
agent on planted defects (both 26/26); both find more of the bibliographies' own errors than the
bare agent (0.88 and 0.83 against 0.74), which is what the script's systematic pass adds.
