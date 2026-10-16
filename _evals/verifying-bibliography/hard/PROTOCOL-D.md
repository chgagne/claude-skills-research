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
