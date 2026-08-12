---
name: surveying-literature
description: Use when finding related work a draft may have missed, checking whether a contribution has already been published, or mapping what a research area looks like. Triggers on "what related work did we miss", "has this been done before", "is our contribution novel", "map this field", "survey the literature on X", or a paper draft whose related-work section looks thin.
---

# Surveying Literature

## Overview

Two modes over one retrieval layer.

**Gap sweep** — from a draft, find work it should have cited. Expands outward from the
bibliography through the citation graph *and* searches the draft's own topic directly,
then grades each candidate by how much it threatens the novelty claim.

**Field map** — from a topic, cluster the area into lines of work and order them
chronologically.

The gap sweep is the one that changes papers. A reviewer who knows the area will name the
omission in the first paragraph of their review; this finds it first.

## Run it

```sh
# gap sweep
python3 ~/.claude/skills/surveying-literature/assets/run-survey.py . \
    --out review-assets/

# what the draft yields, without spending any API budget
python3 ~/.claude/skills/surveying-literature/assets/run-survey.py . --seeds-only

# field map
python3 ~/.claude/skills/surveying-literature/assets/run-survey.py . \
    --field-map "symbolic regression" --out review-assets/
```

Run by absolute path from the paper directory. Stdlib only — no install, no dependencies.

- `--max-per-seed N` (default 20) results per lookup; `--max-angles N` (default 10) topical
  queries. Both bound cost.
- `--min-shared N` (default 3) references two papers must share to cluster in field-map mode.
- Exit code `2` means source coverage was degraded — see *When a source is down*.

Writes `related-work-gaps-<date>.md` + `candidates.json`, or `lit-review-<date>.md`.

**Always run `--seeds-only` first.** It makes no requests and shows exactly what the sweep
will search for. If the angles look wrong, the results will be wrong, and you will have
spent budget finding that out.

## Where candidates come from

Four discovery paths, and the report names which one found each candidate:

| Path | What it reaches |
|---|---|
| `backward` | what the cited papers cite — intellectual ancestors |
| `forward` | what cites them — descendants |
| `related` | the index's own similarity edge |
| `topical` | direct search on the draft's title, abstract concepts and contributions |

**The topical path exists because graph traversal cannot find what the draft is not already
near.** A thin related-work section gives a thin graph neighbourhood — and a thin related-work
section is exactly the defect being looked for. Chat2VIS is one hop from nothing the VIS draft cited;
only topical search reached it.

## Five engines, unioned

| Engine | Character | Notes |
|---|---|---|
| Semantic Scholar | graph API, embedding-flavoured relevance | `S2_API_KEY`, 1 req/s |
| OpenAlex | graph API, different relevance ranking | **paid budget**, see below |
| arXiv | full-text search over abstracts | reports no citation counts |
| Crossref | `query.bibliographic` over published records | polite pool via `mailto` |
| DBLP | near-complete CS venue coverage | reports no citation counts |

**Union, not fallback, for topical search.** The engines rank differently: for "natural
language visualization" OpenAlex returns Chat2VIS fifth, Semantic Scholar does not return it
in twenty, and DBLP finds it where the graph APIs do not. Falling back would consult only the
first engine that answered, and S2 always answers. The *graph* paths do fall back, because
there every engine returns the same edges and a second call buys nothing.

One engine failing costs that engine's results, never the sweep.

**OpenAlex bills per query.** Each search or filter costs $0.001 against a small daily
allowance that resets at midnight UTC; entity lookups by id are free. When it is exhausted,
every request 429s with `Retry-After: 77547` — about 21.5 hours. The retrieval layer caps
Retry-After at 30s and opens the circuit instead of waiting.

## Grading

| Grade | Meaning | What to do |
|---|---|---|
| `THREAT` | On the contribution **and** reached from more than one direction | Respond in the paper: cite and distinguish, or narrow the claim |
| `RELATED` | Topically close, or multiply reached | A one-line citation |
| `BACKGROUND` | Reached once, no topical overlap | Usually noise |

Grade dominates score when sorting, deliberately: a heavily-cited survey that is merely
`RELATED` must never bury the paper that scooped the contribution.

Score is `2×topic overlap + paths + 0.2·log10(1 + citations-per-year) + recency bonus`.

**Citations are per-year, not raw.** Forty citations since 2010 is weaker evidence than
twenty since last year, and recent parallel work is what threatens novelty.

**Unknown citation counts are imputed, not zeroed.** arXiv and DBLP publish no counts.
Scoring their silence as zero would systematically demote recent work — so an unreported
count takes the median of its peers, and the report shows `n/r`.

## When a source is down

- Per-host throttles (arXiv 3.0s, DBLP 2.5s, S2 1.1s, others 1.0s), 3 retries with
  backoff, `Retry-After` honoured **up to 30s**
- Circuit breaker: 3 consecutive failures and the host is dropped for the run
- Cached in `~/.cache/scholarly/`; definitive 404/410 cached too
- Failures are counted, reported on stderr, and set exit code `2`

**Unresolved seeds are reported.** A cited work no index can resolve — an anonymous
artifact, a blog post — means a branch of the graph was never explored. The report says how
many, because a sweep over 14 of 18 references is not a sweep over the bibliography.

## Measured result

Benchmarked against a prior human review of the same draft, which named the gaps a
reviewer would raise. From 18 cited works and 12 angles: **1199 candidates, 31 THREAT**, in ~85s
cold with no degraded sources.

| Named by the human reviewer | Sweep result |
|---|---|
| Chat2VIS | **THREAT** |
| ChartGPT | RELATED |
| LLM code-repair (Self-Debug) | RELATED |
| LLM4Vis | **not found** — see below |

Chat2VIS was reached only through DBLP, and only by topical search — it is one hop from
nothing the draft cites, and the graph-only sweep missed it entirely. That is the whole
argument for unioning heterogeneous engines and for searching the topic directly.

## Limits

- **A gap sweep finds topically adjacent work. It cannot judge whether a paper actually
  threatens the claim** — that is the reviewer's job. `THREAT` means "answer this", not
  "you were scooped".
- **Recall is bounded by the draft's own vocabulary.** Every angle is derived from the
  paper's title, abstract and contributions, so work described in different words can stay
  invisible. LLM4Vis is titled *"Explainable Visualization **Recommendation**"*; the draft
  never uses "recommendation", and no general angle strategy reached it — mixed specificity,
  concept diversity and query broadening each helped other targets and not this one. A
  direct query for `LLM4Vis` finds it instantly, so the index has it and the draft does not
  reach it. **If you know the area, search a term or two by hand;** the sweep complements
  domain knowledge rather than replacing it.
- **Anonymous and non-indexed work is invisible.** Workshop papers and preprints outside
  arXiv frequently are not in any of the five engines.
- Field-map clustering needs reference lists; engines that do not supply them leave papers
  as singletons.

## See also

- `reference/reading-a-gap-report.md` — what to do with each grade
- `reviewing-paper-sources` — Phase 0 offers this skill as an optional module
- `verifying-bibliography` — shares the same retrieval layer in `_shared/scholarly`
