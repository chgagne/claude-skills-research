# surveying-literature, protocol B3: the offline-confirmation method (v3.1) on new drafts

Written 2026-10-12, before any B3 draft was built or probed and before any B3 run. Frozen by the
commit that adds it. A change after the first scored run is a new protocol.

## Question

The v3.1 skill makes eight web searches and confirms candidates through free indexes
(`assets/lookup-titles.py`) instead of searching for each again. On the dev drafts it cost 64% of
the measured version (v2, d6d64fa) and recovered 2 non-memory references against 4, a gap of the
size of v2's own run-to-run variation on those drafts (`../IMPROVEMENT-PLAN.md`, step 0). Does
v3.1 still recover the hard references the bare agent misses, and how does it compare with v2?

## Material

**20 new test drafts.** Pool: the candidates in `private/b3/source_stats_b3.json` that meet
protocol A's eligibility (LaTeX sources with a `.bib`, 25-80 cited references, a related-work,
background or prior-work section), first posted 2026-07 or later, and not among the drafts of
protocols A, B and B2. Order: `random.Random(20261012).shuffle` of the pool sorted by arXiv id.

**Strict key rule (changed from A/B/B2).** A draft is built only if it has at least three
references with a DOI or arXiv id, no leak in the prose, cited in the related-work section and at
least twice in the paper. The fallback to references cited once is not used: a source without
three such references is skipped and logged. Random references as before. Same selection code
otherwise (`build_drafts.py` `choose`, seeded per paper).

Pipeline as protocol B2 (`private/b2/make_b2.sh`): build, `scrub_meta.py`, disguise specs per
draft, `apply_disguise.py`, `anon_links.py`, `fix_filenames.py`, `rename_other.py`; then the B2
leak audit (old names in every text file, author surnames from the arXiv API, e-mails, own links,
missing `\input`s), every finding fixed before the probes. Memory probe as protocol A (no tools,
3 runs per draft). **Floor:** fewer than 15 non-memory key references after 20 drafts means more
drafts are built in the same order until the floor is met or the pool is exhausted, before any
agent run.

## Arms and setup

| Arm | Skill | Runs per draft |
|---|---|---|
| v3.1 | `surveying-literature` on branch `surveying-v31` at **b1594da** | 2 |
| without | no skill | 2 |
| v2 | `surveying-literature` at d6d64fa | 1 |

Everything else as protocols B and B2: prompt (`make_cases.py`), tools, model `claude-opus-5-5`,
80 turns, 40-minute timeout, Bash network grants (Semantic Scholar, Crossref, arXiv export, DBLP
SPARQL), OpenAlex off. The scaffold of every arm also installs the v3.1 `assets/` under the run's
`~/.claude/skills/surveying-literature/`, so the path the v3.1 skill documents works; the other
arms are not told about it. One case at a time behind `_harness/usage_gate.py --five 0.40
--seven 0.75`; runs start after the 7-day window resets (2026-10-14 01:00 local).

## Contamination

As protocol B2: a run is discarded only if the agent requests the source paper by its arXiv id
or DOI (`analyze.py --rule id`). Reported beside it: no discard, and protocol B's title rule.

## Scoring and criteria

`analyze.py` and `score.py` at their committed versions; Recall@30 on non-memory key prior work,
pooled over drafts and runs.

- **Primary:** v3.1 minus without at least **+6 points** (the gain B2 replicated).
- Secondary, reported against their thresholds: v3.1 at least v2 minus 3 points (v2 has one run
  per draft, so this is the least precise comparison); v3.1 cost per run at most 0.7 times v2's.
- Reported beside them: already-cited share per arm, all non-memory and memory-reachable
  references, Recall@10, web searches billed per run (`modelUsage.webSearchRequests`), whether
  each v3.1 run called `lookup-titles.py`, exact McNemar on (reference, run) pairs v3.1 vs
  without.

## Reading the outcome

- Primary met, both secondaries met: v3.1 replaces v2 on main.
- Primary met, a secondary missed: v3.1 is the cheaper method with the replicated gain, v2 is not
  shown to be better; v3.1 replaces v2 and its "Measured result" states the missed secondary.
- Primary missed, v3.1 at or above v2 minus 3: neither version clears the bar on these drafts;
  v3.1 replaces v2 only for its cost, and the paragraph says the gain was not replicated.
- Primary missed and v3.1 below v2 minus 3: v2 stays on main; the branch is kept unmerged.

## Infrastructure failures

A run that ends on an account or session limit is an unobserved run: every run of any affected
case is redone in all arms (`_harness/run_until_clean.py`).

## Amendment 1 (2026-10-14, before any B3 agent run)

The memory probe on the 20 drafts left **9 non-memory key references** (83 of 120 removed
references named from memory, against 55 in B2): the strict key rule selects references central
enough to be named without tools. The 3 reserve drafts cannot reach the floor of 15 at that rate,
and the eligible pool would be exhausted. The pool is extended rather than the criterion
changed. Changes, everything else unchanged:

- **Pool extension.** Candidates from the arXiv API query
  `cat:cs.NE OR abs:evolutionary OR abs:"genetic programming"`, submitted 2026-07-01 to
  2026-10-14, not already in the screened candidate list nor among the drafts of A, B, B2 and B3,
  with cs.NE, cs.LG or cs.AI among their first two categories; screened and filtered by the same
  eligibility and strict key rule (`private/b3/screen_ext.py`, `arxiv_candidates_ext.json`).
- **Order.** The 3 reserve drafts first, in their existing order; then the new candidates,
  sorted by arXiv id and shuffled with `random.Random(20261014)`, are screened in that order
  (576 candidates; screening all would take five hours at arXiv's rate) and the eligible ones
  are built in the same order. Clarified the same day, before any screening.
- **Floor.** Drafts are built, disguised, audited and probed in that order, in batches, until
  the test set holds at least 15 non-memory key references; the draft that crosses the floor is
  the last one. Every built and probed draft stays in the test set.
- **Pipeline.** The B3 pipeline as fixed on 2026-10-14 (`private/b3/NOTES.md`, defects 3-5):
  title and abstract replaced in every .tex, renames applied to style files, `hand_fixes.py`,
  and the scripted leak audit `audit.py`.
