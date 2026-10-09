# surveying-literature: plan to measure and improve

Drafted 2026-10-09. A plan, not a protocol: each stage below gets its own protocol,
committed before its first scored run, as for verifying-bibliography (`../verifying-bibliography/`).

## What is measured

The gap sweep: from a draft, find the work it should have cited. The measurable form is
**held-out citation recovery**. Take a published paper's LaTeX sources, remove some of the
references it really cites (entries and every `\cite` to them), and ask for the missing
related work. A removed reference that comes back is a gap found; the paper's authors are
the ground truth for what belonged.

Two removal policies, reported separately:

- **key prior work**: references cited in the related-work section *and* at least twice in
  the paper. This is the gap a reviewer names, and the case the skill is built for.
- **random**: a uniform draw among the resolvable references, for general recall.

Each paper loses 6 references (3 per policy), all with a DOI or arXiv id so matching is
deterministic. The kept references remain as seeds.

## Material

- **Source papers**: arXiv papers in the user's fields (GP, EC, applied ML) first posted
  after the model's training cutoff (2026-07 onward), with LaTeX sources and 25-80
  references. Post-cutoff papers cannot be recalled from memory; their *references* can,
  which is why the memory probe below matters.
- **Dev set** (6 papers) for iterating on the skill, **test set** (6 papers) frozen and run
  only twice: once on the current skill, once on the improved one. Improvements are judged on
  the test set only; anything tuned on it stops being a measurement.
- **Disguise**: title and abstract paraphrased so that a search for the draft does not land on
  the published paper. Not sufficient alone; see contamination.

## Arms

| Arm | What runs | Why |
|---|---|---|
| without | agent with web tools, no skill | the honest baseline (stage 1 lesson: the bare agent with WebFetch is strong) |
| skill | agent with surveying-literature | the product |
| self | agent with a skill it wrote for itself, frozen once | does the skill beat improvisation |
| script-only | `run-survey.py` alone, no agent, its ranked candidates | isolates the algorithm; cheap and deterministic, so it is the arm the improvement loop iterates on |

Every agent arm ends with the same output contract: a ranked JSON list of at most 30
candidates, each with title and DOI or arXiv id.

## Metrics

- **Recall@10 and Recall@30** of the held-out references, per removal policy (primary:
  key prior work, Recall@30).
- **Rank** of each recovered reference (mean reciprocal rank).
- **THREAT alignment** (skill and script-only): share of recovered key-prior-work references
  graded `THREAT`.
- **Precision proxy**: share of the top 30 that the paper cites (kept seeds excluded), plus a
  blind judge on a fixed sample for whether a non-cited candidate is genuinely related. The
  proxy alone undercounts: a good sweep finds related work the authors also missed.
- Cost, time and API calls per run.

## Memory probe (before freezing)

The bare model, no tools, gets each disguised draft three times and lists the related work
it thinks is missing. A held-out reference it names is **memory-reachable**. Unlike planted
bibliography defects, knowing a field is a real skill, so these references are kept, not
replaced; recall is reported on both subsets, and the **primary metric is recall on the
references the probe did not name**, where retrieval has to do the work.

## Contamination

- A run is discarded if its trace fetches the source paper itself: its arXiv id, DOI,
  Semantic Scholar id, or its exact title as a query.
- The script's forward path can list the source paper among the papers citing a seed. That
  candidate is excluded from scoring, and fetching its reference list counts as contamination.
- Stage-1 lesson kept: the leak check is the trace, never "the without arm scored high".

## Harness issues to settle first

1. **Semantic Scholar key.** `claude plugin eval` gives each run a fresh HOME and injects
   only `EVAL_*` variables, so the skill would run on S2's anonymous rate and fail. Options:
   have retrieval also read `EVAL_S2_API_KEY` (smallest change), or run the agent arms outside
   the plugin-eval sandbox. Decide in a smoke run.
2. **OpenAlex budget.** About 100 free search queries a day; one sweep can spend most of it,
   and an exhausted budget silently changes what an arm sees. Either exclude OpenAlex from
   every arm for the measured runs, or spread runs across days with a per-run budget check.
   Same rule for all arms.
3. **Wall time.** A sweep is ~85 s cold before DBLP's new 10 s crawl delay; ten topical angles
   through DBLP add about 2.5 minutes. Measure in the smoke run and set the timeout from it.
4. **Shared code** with verifying-bibliography (`extract.py`, `score.py`, the probe driver)
   moves to `_evals/_harness/` before this suite is written.

## Improvement loop (dev set, script-only arm first)

Candidate changes, each from a documented limit in the skill:

| Limit (SKILL.md) | Candidate change |
|---|---|
| Angles are n-grams from the abstract's opening; generic openings give junk angles | let the agent supply angles (`--angles`) written from the whole draft, the n-gram extractor as fallback |
| Recall bounded by the draft's vocabulary (LLM4Vis) | agent-written synonym and adjacent-term queries; S2 recommendations endpoint as a fifth graph path |
| Ranking by topic overlap of words | rerank with SPECTER embeddings that S2 returns (cosine in stdlib) |
| OpenAlex budget, DBLP latency | measure each engine's marginal recall on the dev set; drop or reorder engines that add nothing |

Each change is kept only if it raises dev-set Recall@30 (key prior work) without lowering
precision, measured with the script-only arm (no LLM cost). Changes that need the agent
(agent-written angles) are checked with the skill arm on the dev set.

## Stages

1. **Smoke** (1 dev paper, skill arm, 1 run, unscored): settle the S2 key, OpenAlex and
   timeout issues; check that traces and final JSON are recoverable.
2. **Baseline** (protocol A): test set, 4 arms, 3 runs. Criterion written before running.
3. **Improve** on the dev set, script-only first, as above.
4. **Re-measure** (protocol B): the improved skill on the same frozen test set, same arms.
   The comparison of stage 2 and stage 4 is the result.

Rough cost, from verifying-bibliography: agent runs here are longer, about $1-2 each. Stage 2
is 6 papers x 3 runs x 3 agent arms = 54 runs, about $60-100, plus free script-only runs.

## Decisions (user, 2026-10-09)

- **Source papers**: post-cutoff arXiv papers in the user's fields (GP, EC, applied ML),
  12 in all (6 dev, 6 test). The group's own papers are not used.
- **Harness**: agent arms run inside `claude plugin eval`; the shared retrieval layer also
  reads `EVAL_S2_API_KEY`, so the fresh HOME keeps its Semantic Scholar key.
- **OpenAlex**: disabled in every arm for the measured runs; its marginal recall is
  measured separately on the dev set.
- **Success criterion** for stage 2 and stage 4: at least +15 points of Recall@30 on
  non-memory key prior work over the without arm, with precision not lower.
