# Protocol C1: comparing-papers on planted comparison discrepancies

Written 2026-10-29, before any paper was listed or any discrepancy planted. Design
settled with the researcher in a question round the same morning (journal `2026-10-29.md`).
Planted discrepancies; skill vs bare; competitors published after the model's cutoff; dev 4 +
test 8, 2 runs per arm.

## Question

Does the skill help an agent notice that a draft misstates its comparison with a named competitor
when the agent would miss it on its own? The skill fetches the competitor's text (LaTeX source
first). It computes notes on training scale and seed count only, and shows quoted passages on six
other axes. Its only measurement so far is one case (the SNIP scale gap).

## Material

**Pool.** Pairs (D, C). D is an arXiv submission from 2026-08-15 to 2026-10-25, primary category
cs.LG, cs.CL, cs.CV or stat.ML. C is an arXiv paper first submitted on or after 2026-07-01 (after
the model's training cutoff) and cited by D. The arXiv API lists D candidates, screened in a
shuffled order (seed 20261029). A pair is eligible when:

- D's LaTeX source flattens to a single `.tex` (inputs inlined, comments stripped);
- C appears by name or citation in a results table of D;
- C has LaTeX source on arXiv, and that source states at least one of: training scale (steps,
  epochs, examples or tokens), a seed count, or the headline number D reports for it;
- no author of D or C is in the researcher's group.

The first 12 eligible pairs are used: 4 dev and 8 test, in screening order (first 4 dev).
At most one pair per C.

**Disguise.** The original D is online and would be an answer key. D's `\title`, authors,
affiliations, acknowledgements, emails and repository links are replaced or removed (B2's
`scrub_meta.py`, plus a manual pass recorded per pair). C is named by its real arXiv id: fetching
it is the task.

**Plants.** One plant per case, at most 3 source lines of D, contradicting a passage of C that is
recorded with its section. Three types:

- **scale**: D's description of how it trained or ran C shrinks the budget to at most one third of
  C's published one (steps, epochs, data or tokens), while D still says it follows C's setup;
- **seeds**: D misstates C's seed or run count, or claims parity with C's protocol on seeds when
  the counts differ;
- **quote**: a number D reports for C in a results table, said to be taken from C's paper, is
  changed by enough to change or widen D's stated advantage.

A plant is valid only when (a) C's text contradicts it, with the passage recorded; (b) the
original D lines agree with C (a pair whose original already disagrees keeps that disagreement as
a natural discrepancy, recorded, and gets its plant elsewhere); and (c) nothing else in D is
edited. A subagent proposes plants from a fixed prompt; Claude checks (a)-(c) and records the
check. Plants are stored in `private/plants/<case>.json` (original lines, new lines, C passage,
line span).

**Memory probe.** For each C, the bare model without tools is asked for C's training scale, seed
count and the reported number on the plant's metric. A pair whose plant the probe answers
correctly is replaced by the next eligible pair.

## Calibration (dev, bare agent only)

4 dev pairs x 3 types = 12 cases, bare agent twice each (24 runs). Per type, dev recall is hits/8.

- recall <= 0.50: the type is kept as is;
- recall > 0.50: the type's rule is made subtler once, written down before the re-run (the plant
  sits outside the results section, or the changed number stays within the draft's stated
  margin), 4 new dev plants of that type are built, and the bare agent reruns them twice. The
  type is kept if recall is now <= 0.50, dropped otherwise;
- every type dropped: C1 stops before test, and the report says the bare agent catches these
  plants and this design cannot separate the arms.

No skill run on dev; the skill is not edited during C1.

## Arms

| arm | what it is |
|---|---|
| `skill` | the published comparing-papers skill, frozen at the commit recorded when test cases are built |
| `without` | the same agent with no skill |

Both arms use claude-opus-5-5 with the same tools: Read, Write, Edit, Bash, Glob, Grep, Skill,
WebFetch. Network is granted per host and identically in both arms: arxiv.org, export.arxiv.org,
api.openalex.org, api.crossref.org. There is no WebSearch, because C is named and nothing needs
searching. Each run gets 40 min, 100 turns and `--max-cost-usd 20`. Test is 8 cases x 2 arms x 2
runs = 32 runs, launched one case at a time behind `usage_gate.py --five 0.40 --seven 0.75`.

**Prompt** (identical in both arms): a co-author's draft is in the working directory; it compares
against C (arXiv id given). Check whether the comparison with C is fair and correctly reported.
End with a JSON block `{"issues": [{"draft_quote": "<at least 20 characters copied verbatim from
the draft>", "competitor_evidence": "<what C says, and where>", "problem": "<what is wrong>"}]}`,
or an empty list. The prompt does not name the axes.

**Contamination.** A run whose trace fetches D's arXiv id, or searches for D's original title, is
discarded and rerun once. A second contaminated run is reported, not replaced.

## Scoring

- **Hit**: a scoring script, committed before any test run, locates every issue whose
  `draft_quote` overlaps the plant span widened by 3 lines. Each located issue is then read by
  content: it is a hit only when its `problem` names the planted quantity and the direction of
  the discrepancy. Script first, then a content check by Claude, arm-blind (runs shuffled, arm
  labels hidden).
- **Other issues**: every issue that is not a hit. Each is adjudicated arm-blind as real
  (contradicted or unsupported by C's or D's text), false, or a matter of judgement. A natural
  discrepancy recorded at build time counts as real.

## Criteria (test)

- **Primary**: plant recall, skill minus bare, at least +0.15 (16 runs per arm; direction only,
  McNemar reported).
- **Secondary**: false issues per run, skill at most 1.5 times bare; cost per run reported.

| Outcome | What follows |
|---|---|
| primary met, secondary met | keep; SKILL.md gets a measured line |
| primary met, more false issues | keep; read the false issues before any change |
| primary not met, skill within 0.15 of bare | report; discuss reducing the skill with the researcher (as D and P2), no automatic change |
| skill below bare by more than 0.15 | read the traces; discuss with the researcher |

**Stage-2 trigger** (written now): primary met but McNemar p > 0.10 → 8 more test pairs, the same
rules, pooled.

## Budget

About 56 runs (24 dev + 32 test), roughly $60-110 at $1-2 per run; screening and the memory
probe a few dollars more.

## Amendment 1 (2026-10-29, after screening, before any plant or probe)

Screening (`private/c1/pool.py`, 1,078 drafts screened, 48 candidate pairs from 30 drafts) and a
fact sheet per pair (subagents, quotes with line numbers, `private/c1/elig/`). The researcher
chose two changes:

1. **One pair per draft.** Seven candidate pairs share one draft. Exactly 12 pairs are eligible
   with this rule, in screening order: dev = pairs 2, 3, 6, 7; test = 8, 9, 10, 11, 14, 15, 18,
   24 (numbers from `private/c1/pairs.json`). Spares, in order: 35 (the shared draft, once), 41.
2. **Dev plants: 4 per type, at most 2 per pair.** A quote plant needs a number the draft says it
   took from the competitor; a seeds plant needs a stated seed or run count. Among the dev pairs,
   scale fits 4, seeds 3, quote 2. Dev keeps 12 cases (4 per type) and one type may be planted
   twice in one pair at different locations. Test is unchanged: one plant per pair, and types are
   rotated over the kept types that the pair supports.

The fact sheets are subagent output. Every fact a plant relies on is checked by Claude against the
sources when the plant is built.

## Amendment 2 (2026-10-29, after calibration round 1, before any subtler plant)

**Calibration round 1** (24 bare runs, 12 dev cases, $21.8): recall 1.00 for every type (scale
8/8, seeds 8/8, quote 8/8); no contamination, no format failure. Each plant named the competitor
in the planted lines, where an agent told which paper to compare with is already looking.

**Subtler rule** (the researcher's choice, written before any round-2 plant):
- every type: the planted lines do not contain the competitor's name, method name or cite key.
  The plant refers to it indirectly, for example "all baselines", "the base paper", a caption or
  table note that covers the competitor's row, or a hyperparameter table;
- scale: the budget is stated in other units than the competitor's (for example steps x batch
  against epochs x dataset size), so the shortfall to at most one third appears only after
  arithmetic;
- seeds: the misstatement covers the competitor through a shared statement (a caption, a
  "for all methods" sentence), not by name;
- quote: one number the draft takes from the competitor changes by at most 1 point and does not
  flip the ordering of the draft's method and the competitor on that column.

Rules (a)-(d) of the plant prompt still apply. 4 new dev plants per type on the dev pairs (2, 3,
6, 7), at most 2 per type per pair, at locations not used in round 1. The bare agent runs them
twice (24 runs). A type is kept if its round-2 recall is <= 0.50, dropped otherwise; test plants
of a kept type follow the round-2 rule. If every type is dropped, C1 stops before test.

## Amendment 3 (2026-10-29, during round-2 plant checks, before any round-2 run)

A quote plant edits the competitor's own table row, which is usually labelled with its name; only
pair 6 labels it indirectly ("Base paper"). The researcher chose: for the quote type the row label
may name the competitor; the subtlety is the change of at most 1 point without an ordering flip.
The other types keep amendment 2's no-name rule.

## Amendment 4 (2026-10-29, after calibration round 2, before any test plant)

**Round 2** (24 bare runs, 12 subtler dev cases, $21.4; content verdicts in
`private/c1/verdicts_dev2.json`): quote 8/8, seeds 5/8 (strict reading: a hit names the seed count
and its direction; two vague "protocol does not match" issues not counted), scale 3/8.
Quote and seeds are dropped.

**One scale plant excluded** (the researcher's choice). Pair 6's plant at line 686 ("the base
paper's recipe on 2,000 sequences") states the same quantity the draft already gets wrong at line
246 (batch 8 vs 32, one epoch: 2,000 vs about 12,000 sequences). Both runs flagged "2,000 vs 12,000"
but quoted line 246. Rule (b) is meant to keep plants off quantities the draft already misstates;
this plant breaks it in substance although it sits 440 lines away. Without it, scale is 3/6 = 0.50:
**kept** (bar <= 0.50). By location it would be 3/8; counting the line-246 flags by content, 5/8.

**Test** is scale only, under amendment 2's rule (no competitor name in the planted lines, budget in
other units, shortfall to at most one third visible only after arithmetic). Pairs whose competitor
states no training scale (10, 14) are replaced by the spares in order (35, 41): test pairs 8, 9,
11, 15, 18, 24, 35, 41. A test pair that cannot host a valid scale plant is reported to the
researcher before any test run. The primary criterion is unchanged (skill minus bare >= +0.15 on
16 runs per arm).
