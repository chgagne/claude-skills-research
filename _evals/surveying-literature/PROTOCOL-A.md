# surveying-literature, protocol A: baseline on the test set

Written 2026-10-09, before any scored run. Frozen by the commit that adds it. Plan and
decisions: `PLAN.md`. A change after the first scored run is a new protocol.

## Question

On drafts from which real citations were removed, does an agent with `surveying-literature`
recover the missing related work better than the same agent without it, and better than a
skill the agent wrote for itself?

## Material

30 arXiv papers first posted 2026-07 to 2026-10 (GP, EC, applied ML), LaTeX sources with
25-80 cited references and a related-work section. 12 were drawn first; 18 more were drawn
with a seed from the 31 remaining eligible papers after the first memory probe showed too few
non-memory references (`private/expansion.json`). **Test: 20 papers. Dev: 10**, untouched here.

Per paper, 6 cited references with a DOI or arXiv id were removed from every `\cite` and from
the `.bib`: 3 **key prior work** (cited in the related-work section and at least twice; one
paper had only 2 and took a third cited once there) and 3 **random**. A reference whose first
author's surname or distinctive name appears in the prose was never removed.

Each draft is disguised: title and abstract paraphrased without exact numbers, the method's
name and coined terms renamed everywhere (prose, labels, colours, file names), the authors'
own repository links replaced, author block anonymised, comments and `.bbl` dropped, root file
renamed `main.tex`. Build: `private/make_drafts.sh` from the arXiv sources, deterministic.

**Memory probe** (no tools, 3 runs per draft): a removed reference named in any probe is
`memory`. Test set: 120 removed references, 67 memory, **20 non-memory key prior work**,
33 non-memory random. The label leak (`\label{subsec:<method>}`) was closed after the probes;
probes saw the leakier drafts, which can only have raised the memory count.

Drafts and labels stay in `private/` (gitignored): the sources carry their own licences.

## Arms

| Arm | Runs | Setup |
|---|---|---|
| without | 3 per paper | no skill |
| skill | 3 per paper | `surveying-literature` at commit ddaf6ff |
| self | 3 per paper | `self-surveying-literature`, written once by Claude in an isolated Write-only session, frozen by sha256 in `self-skill.sha256` |
| script | 1 per paper | `run-survey.py` alone, its own top 30 (`run_script_only.py`) |

Agent arms: `claude plugin eval`, `--model claude-opus-5-5`, identical prompt (`make_cases.py`),
tools Read Write Edit Bash Glob Grep WebFetch WebSearch Skill, 80 turns, 40-minute timeout,
`--scaffold` installing the draft, the frozen `_shared` and the S2 key file in each run's HOME,
Bash network granted for api.semanticscholar.org, api.crossref.org, export.arxiv.org and
sparql.dblp.org in every arm, OpenAlex switched off in every arm (`EVAL_SCHOLARLY_DISABLE`).
At most 2 skill runs at a time (they share one Semantic Scholar key at 1 req/s).

## Scoring (`score.py`)

The final message's last `json` block gives at most 30 ranked candidates; the source paper
itself is removed before ranking. A candidate matches a removed reference on DOI, arXiv id,
equal normalised titles, a 6+-word title prefix, or title similarity >= 0.88.

- **Primary:** Recall@30 on **non-memory key prior work**, pooled over the 20 papers and runs.
- Secondary: Recall@30 and @10 on every subset (key/random x memory/non-memory), mean
  reciprocal rank, share of candidates the draft already cites, THREAT grade of recovered key
  references (skill and script arms).
- Covariate per run: source failures reported by the sweep (degraded coverage), turns, cost,
  wall time.
- A run with no parseable block counts as recovering nothing.

## Success criterion

The skill arm succeeds if **both** hold:
1. its primary recall exceeds the without arm's by at least **15 points**;
2. its share of candidates already cited by the draft is not higher than the without arm's.

The same two comparisons against the self arm are reported; the criterion is against without.
Indicative: exact McNemar on (reference, run) pairs, skill vs without.

## Contamination

A run is discarded and reported if the agent itself fetches the source paper: a WebFetch or
shell request for its arXiv id or DOI, or a WebSearch query containing 60% or more of the words
of its original title. The source appearing in a tool's results (the sweep's forward path can
list it) is not contamination; it is removed before scoring.

## What follows

No automatic further stage. Whatever the outcome, the improvement loop runs on the dev set
(`PLAN.md`), and protocol B re-measures the improved skill on this same frozen test set.

## Known before running

- In the smoke run the sweep reported 5 Semantic Scholar and 3 DBLP failures; failures are a
  covariate, not a reason to discard a run.
- The sweep's angles come from the abstract's opening; paraphrased abstracts change them.
  That is part of what the skill does with a real draft, and is not corrected here.
