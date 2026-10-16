# verifying-bibliography, protocol D: long bibliographies and entries without identifiers

Written 2026-10-16, before any case was built. Frozen by the commit that adds it; the case
set, the memory filter's outcome and the smoke run are recorded in an addendum committed
before the first scored run. A change after the first scored run is a new protocol.

## Question

Protocol C (`../longtail/PROTOCOL-C.md`) put every arm at ceiling: on six 10-entry
bibliographies the bare agent queried Crossref and arXiv itself and found every defect. Does
`verifying-bibliography` find more substantive errors than the same agent without it, or than a
skill the agent wrote for itself, when the bibliography is long and many entries carry neither a
DOI nor an arXiv id?

## Material

**Sources.** The cited bibliographies of six published arXiv papers (2026-07 to 2026-10) whose
LaTeX sources are held locally for the surveying-literature benchmark
(`../../surveying-literature/private/src/`). Published papers only; no unpublished draft.

- **3 long**: the three sources with the most cited references (74 to 77).
- **3 identifier-poor**: among sources with at least 40 cited references, the three with the
  highest share of references carrying neither DOI nor arXiv id after a Crossref title search
  (43% to 48%).

Each bibliography is every cited entry of its source, in the source's order, re-emitted from
the parsed fields (formatting is out of scope). Entries with no title or no author (web pages,
software) are dropped.

**Planted defects: 5 per bibliography, 30 in all**, chosen by a seeded draw per bibliography
(`random.Random("bib-hard:<arXiv id>")`) among eligible entries:

| Label | Defect | Eligible entries |
|---|---|---|
| `metadata` | page range shifted by 3 to 30 | entries with a page range and no DOI |
| `authors` | an invented co-author inserted (not first) | the five oldest entries with 2+ authors |
| `nonexistent` | a fabricated workshop paper from 2003-2009 in the bibliography's field | added entry |
| `metadata` | venue replaced by another entry's venue of the same kind | journal or proceedings entries |
| `preprint` | a published entry replaced by its arXiv preprint form | entries whose arXiv version exists |

Before planting, each target's original record (pages, author list, venue, publication) is
checked against Crossref or DBLP; a target that cannot be confirmed is redrawn. A fabricated
entry must have no match in Crossref, DBLP or arXiv by title.

**Memory filter**, as the long-tail protocol: each case is given 3 times to the bare model
(`claude-opus-5-5`, no tools, no skill) with the protocol prompt. A defect flagged with its
label in any probe is replaced by a new draw of the same row, and the case is probed again,
until no defect is caught from memory or a row has no eligible entry left (recorded).

**Natural errors.** Real bibliographies carry their own errors. After all runs, every flagged
entry that is not a planted defect is adjudicated once, blind to the arm, against the primary
record (Crossref, DBLP, the proceedings page). A confirmed substantive error is excluded from the
false-positive count and reported as a natural find per arm; an unconfirmed flag is a false
positive.

**Labels stay private** (`private/gold.json`) until the results are recorded.

## Arms

- **without**: no skill.
- **skill**: `verifying-bibliography` at the commit named in the addendum.
- **self**: the frozen self-written skill (`../self-skill/`, sha256 unchanged).

Model `claude-opus-5-5`; the protocol C prompt, scaffold and Bash network grants; 100 turns and a
40-minute timeout (long bibliographies). **2 runs per case** (36 runs), one case at a time behind
`_harness/usage_gate.py --five 0.40 --seven 0.75`. One unscored smoke run (skill arm, longest
bibliography) before the addendum checks that the limits suffice.

## Contamination

A run is discarded if its trace mentions `gold.json` or `_evals`, or requests a source paper by
its arXiv id or DOI (the source's own bibliography holds the correct records).

## Scoring and criterion

`../score.py` against the private gold, after the natural-error adjudication.

- **Success**: skill pooled recall on planted defects at least **20 points** above both the
  without and the self arms, and its false-positive rate not higher than either.
- Reported beside it: recall per case kind (long, identifier-poor) and per label, label accuracy,
  natural finds, whether the script ran in each skill run, entries the trace shows were checked,
  cost per run and per entry.

## Reading the outcome

- Without at or near ceiling (recall 0.9 or more): the skill is worth only its script's
  systematic pass; it is reduced to "run the script, read the report" and the rest removed.
- Without well below ceiling and the criterion met: the gain is measured and the skill keeps its
  justification as written.
- Without well below ceiling and the criterion missed: the skill does not close the gap; its
  checks are compared with the misses to find what neither arm reaches.

## Amendment 1 (2026-10-16, before any agent run)

**What the memory filter found.** Two rounds of probes (3 runs per case, no tools) caught 51 of
the 54 distinct defects planted across both draws: every fabricated entry (12 of 12, the model
calls an entry it does not know nonexistent), every preprint substitution (12/12), every venue
swap (12/12), every invented co-author (9/9, the one round-1 survivor caught in round 2), and 6
of 9 page shifts. On bibliographies of recent machine-learning papers, the bare model's memory
alone finds almost every defect of these kinds; only page ranges of papers it knows without
knowing their pages survive.

**Change.** Only the `metadata`/pages row is kept. Per bibliography, **3 page-shift defects**,
each on a separate entry with a page range, no DOI, a record confirmed by DBLP or Crossref
(same page range) and no duplicate title in the bibliography; shift drawn per entry
(`random.Random("bib-hard:pages:<arXiv id>:<key>")`, 3 to 30). Candidates are taken in the
existing draw order; entries caught in an earlier round are never redrawn. The memory filter is
repeated on the whole case until 3 defects per bibliography survive or the row is exhausted
(recorded). Expected: about 18 defects in about 370 entries.

The criterion, arms, runs, natural-error adjudication and reading are unchanged; with a single
defect class, label accuracy is trivial and not reported. Runs start after the 7-day window
resets (2026-10-21 01:00); before that the window is above the gate's ceiling.

## Addendum (2026-10-16, before the first scored run)

- **Sources** (selection code `private/build_hard.py`): long 2608.21927, 2609.14896, 2608.07539
  (77, 77, 76 cited entries); identifier-poor 2610.18085, 2608.13296, 2610.10394. Their share of
  references without DOI or arXiv id is 48% to 76%, not the 43% to 48% written above from an
  earlier count; the selection rule is the one stated, unchanged.
- **Memory filter, page shifts** (amendment 1): five more rounds; 39 page shifts caught from memory in
  all. Final set: **13 defects** in 364 entries: 3 each in long1, poor1 and poor2, 2 each in long2
  and long3 (row exhausted), none in poor3 (row exhausted: every eligible entry caught). poor3
  stays in the set as a bibliography with no planted defect; it counts toward false positives.
- **Skill** frozen at bf62212 (`verifying-bibliography` and `_shared`); self-written skill
  sha256 unchanged.
- **Smoke run** (skill, long2, unscored): 17 turns, 9 minutes, $1.24; the script ran; both
  planted defects flagged; 24 other entries flagged, 23 of them as preprints, so the natural-error
  adjudication will carry most of the false-positive count.
- **Grants** as protocol C, OpenAlex included. Runs start after 2026-10-21 01:00.
