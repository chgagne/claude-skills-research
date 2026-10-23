# verifying-bibliography, protocol E: the reduced skill on fresh bibliographies

Written 2026-10-23, before any case was built. Design settled in an interview the same day
(`../../journal/2026-10-23.md`). Frozen by the commit that adds it.

## Question

The reduced skill (published at 00dd1af, SKILL.md as validated at 61ee681) was revised twice on
protocol D's six bibliographies. On bibliographies it has never seen, does it find the
bibliographies' own errors at least as well as the full skill it replaced, at no higher cost?

## Material

Six cited bibliographies of published arXiv papers from the local surveying-literature source
pool, none used in protocol D, chosen by D's rule (`hard/private/build_hard.py`, `pick_sources`)
applied to the remaining pool:

- **3 long** (most cited entries): 2610.01583 (76), 2608.13952 (74), 2609.39048 (72).
- **3 identifier-poor** (highest share of entries with neither DOI nor arXiv id, among sources
  with at least 40): 2610.03833, 2609.10980, 2610.10807.

Each bibliography is every cited entry with a title and an author, re-emitted from the parsed
fields as in D. **Nothing is planted** and there is no memory filter: the measure is the errors
the bibliographies already contain.

## Arms

- **reduced**: `verifying-bibliography` at 61ee681 (the published reduction).
- **full**: `verifying-bibliography` at bf62212 (the version D measured).
- **without**: no skill.

Same model (`claude-opus-5-5`), prompt, scaffold, grants, 100 turns and 40-minute timeout as D;
`_shared` at bf62212 for both skill arms. **2 runs per case, 36 runs**, one case at a time behind
`_harness/usage_gate.py --five 0.40 --seven 0.75`.

## Contamination

As D: a run is discarded if a tool call touches `_evals` or `gold.json` outside the frozen install
paths, or names the source paper's arXiv id; search results that merely list the source do not
count. A discarded or usage-limited run is re-run once.

## Scoring

Every flagged entry, from any arm, is adjudicated once from a sheet that shows the entry and the
labels given but not the arm, by D's rules: a preprint flag is confirmed when DBLP or Crossref
holds a peer-reviewed record with the same title; other flags against DBLP, Crossref, the
proceedings page or the organisers' page; CVF open-access pagination counts as correct; an error
not confirmed by such a record is a false positive. The natural pool is the confirmed errors; an
arm's recall is its hits over (pool errors in the case x runs).

## Criterion (all must hold)

1. Reduced natural recall at least the full skill's minus 0.05.
2. Reduced false positives at most 1.5 times the full skill's.
3. Reduced mean cost per run at most 1.3 times the full skill's.
4. The script ran in at least 11 of 12 reduced runs.

Reported beside it: each skill arm minus the bare agent on natural recall; recall by label and by
case kind; web searches per run.

## Reading

- All met: the reduction stands; the journal's open question closes.
- Any failed: no automatic revert. The failing runs' traces are compared with the full skill's to
  find the instruction that mattered, and the fix or the revert to bf62212 is decided with the
  researcher before anything is published.

The pool holds only errors some run flagged, so recalls are relative to the union of finds.
