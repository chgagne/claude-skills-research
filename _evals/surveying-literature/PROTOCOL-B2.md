# surveying-literature, protocol B2: replication of protocol B on new drafts

Written 2026-10-11, before any new draft was built or probed and before any protocol-B2 run.
Frozen by the commit that adds it. A change after the first scored run is a new protocol.

## Question

Protocol B found +18.1 points for the search-method skill under its contamination rule, but
+11.7 with no run discarded, and that rule (60% of the original title's words in a WebSearch
query) discarded 9 skill runs against 3 without. Does the gain reach the 15-point bar on
references the protocol has never seen, under a contamination rule that targets only the
actual leak (fetching the source paper)?

Protocol B's 20 test drafts hold only 20 non-memory key references; rerunning them would add
runs, not references. B2 therefore uses new drafts.

## Material

**20 new test drafts.** Pool: the screened candidates in `private/source_stats.json` that meet
protocol A's eligibility (LaTeX sources with a `.bib`, 25-80 cited references, a related-work,
background or prior-work section), first posted 2026-07 or later, and not among the 30 drafts
of protocols A and B. Order: `random.Random(20261011).shuffle` of the pool sorted by arXiv id;
drafts are built in that order, a source that cannot be built (no resolvable references to
remove, sources that do not compile into one root file) is skipped and logged, until 20 are
built. No dev split: the skill is not tuned on these drafts.

Per draft, as protocol A: 6 cited references with a DOI or arXiv id removed from every `\cite`
and from the `.bib`, 3 key prior work and 3 random, same selection code; same disguise
(title and abstract paraphrased without exact numbers, method name and coined terms renamed
everywhere including labels and file names, authors' repository links replaced, author block
anonymised, comments and `.bbl` dropped, root renamed `main.tex`), same leftover checks.

**Memory probe** as protocol A (no tools, 3 runs per draft). **Floor:** if the 20 drafts give
fewer than 15 non-memory key references, further drafts are built in the same shuffled order
until the floor is met or the pool is exhausted. Probes are not scored runs; this happens
before any agent run.

## Arms and setup

**skill** (`surveying-literature` at **d6d64fa**, the version protocol B measured; the only
later change is the informational "Measured result" paragraph) and **without**, in one
`claude plugin eval --ablation with-without` call, **2 runs per draft**. Everything else as
protocols A and B: prompt (`make_cases.py`), tools, model `claude-opus-5-5`, 80 turns,
40-minute timeout, scaffold, Bash network grants, OpenAlex off, at most 2 runs at a time.
Runs launched one case at a time behind `_harness/usage_gate.py --five 0.40 --seven 0.75`.

## Contamination (changed from protocols A and B)

**Primary:** a run is discarded only if the agent itself requests the source paper by
identifier: a WebFetch whose URL, or a shell command whose network request, contains the
source's arXiv id or DOI (the id branch of `contamination.py`). A WebSearch query close to the
original title is not a discard: search results show snippets, not the reference list. The
source appearing anywhere in tool results is not contamination; it is removed from the
candidates before scoring, as before.

**Sensitivity, reported beside it:** (a) no run discarded; (b) protocol B's rule (id or 60% of
title words).

## Scoring and criterion

Unchanged: `analyze.py` and `score.py` at their committed versions. Primary: Recall@30 on
non-memory key prior work, pooled over the B2 drafts and runs. The skill succeeds if its
primary recall exceeds the without arm's by at least **15 points** and its already-cited share
is not higher. Indicative: exact McNemar on (reference, run) pairs.

Reported beside it: the same with no discard; all non-memory and memory-reachable references;
Recall@10; cost and time per run; and, as a secondary analysis only, protocols B and B2 pooled
under the primary rule above (B's no-discard result was already known when this was written,
so the pooled figure cannot decide anything).

## Reading the outcome

- Criterion met in B2 under the primary rule and the no-discard figure within a few points: the
  gain is replicated; the skill stays as is.
- Criterion not met but skill above without: the gain is real but smaller than the bar; the
  skill stays, and its "Measured result" paragraph states the B2 figure as the estimate.
- Skill at or below without: protocol B's result did not replicate; the paragraph says so and
  the search method is reconsidered against its 2.5x cost.

## Infrastructure failures

A run that ends on an account or session limit is an unobserved run: every run of any affected
case is redone in both arms (`_harness/run_until_clean.py`).
