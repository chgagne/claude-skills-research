# Protocol W3: a category form the writing report must answer

Written 2026-11-11, before any material, variant or run. Target, material and design ruled by the
researcher in one interview the same day (journal `2026-11-11.md`): a per-category form for
proofreading-paper-writing, W1's drafts as a non-regression guard plus 6 fresh unplanted drafts for
the primary, full arms (72 runs), the form as a category table in `writing-report.md`.

## Why

Three structural changes so far moved coverage or stability where prose did not: C2's budget list,
R3's fixed review form, R5b's one-row-per-float §6 with its checker. In W1 the skill's only gain was
one rubric line (intensifiers, 0.94 vs 0.39), and its proposals were not more stable across runs
than the bare agent's (0.817 vs 0.849; reduced skill 0.842 in W2). W3 asks: **does a writing report
that must answer every rubric category, enforced by a checker, make each run cover more of a draft's
real writing defects, and cover the same ones across runs?** It measures coverage and stability on
unplanted drafts, not recall of plants.

## The variant (branch `proofread-form`, built after this protocol is committed)

- `writing-report.md` gets a **Checklist** table with one row per rubric category (about 14, taken
  from `reference/critique-rubric.md`: e.g. agreement/articles/tense; duplicated words; citation
  punctuation; `\ref`/Figure form against the paper's convention; hyphenation and capitalisation
  consistency; wordiness; intensifier or vague quantifier where a number exists; stacked hedges;
  overloaded sentences; topic sentence and transitions; redundancy across sections; term used before
  definition or two names for one concept; contribution list vs results; abstract/introduction/
  conclusion agreement). Each row lists the `W` ids found or `none: checked <where>`.
- Ledger rows gain a `category` field. `assets/check-writing-form.py writing-report.md --ledger
  writing-ledger.jsonl` fails when a category row is missing, unanswered, cites an id absent from
  the ledger, or cites a row whose `category` differs. SKILL.md step 2 gets one sentence naming the
  categories, step 4 one sentence requiring the checker to pass. Nothing else changes: same rubric,
  gate, caps, renderer.
- Dev gate (below) only: the category list may be adjusted on dev drafts before the freeze.

## Material

**Fresh drafts (primary).** R5's pool (post-cutoff arXiv, v1 2026-08-01 to 2026-10-31, primary
cs.LG/cs.CV/cs.CL), screened in R5's shuffled order (seed 20261110) from the first unscreened
position. Eligible: the source flattens to one `.tex`; it **compiles locally** with `latexmk -pdf`
in under 3 minutes with the files in the source; main text 4,000 to 12,000 words; no author in the
researcher's group; not one of R5's 8 papers. First 8 eligible: 2 dev, 6 test, in screening order.
No disguise and no memory check: runs have no web tools, and knowing a paper does not help find
defects in its prose. Drafts are not edited.

**W1's drafts (guard).** W1's six planted cases (`private/w1/cases/w1_*`, 29 plants), unchanged.

## Arms and runs

| arm | what it is |
|---|---|
| `form` | proofreading-paper-writing at `proofread-form`, frozen when the test cases are built |
| `current` | the skill as published (W2 reduction, merged 686f6e4), frozen at the same time |
| `without` | the same agent, no skill |

W1's prompt verbatim (`make_cases_deliver.py`), W1's settings: claude-opus-5-5, tools Read, Write,
Edit, Bash, Glob, Grep, Skill, Agent, no web, 200 turns, 60 min. Deliverables kept by the launcher.

- Fresh: 6 drafts x 3 arms x 3 runs = **54 runs**.
- Guard: W1's 6 drafts x `form` x 3 runs = **18 runs**, compared with W2's reduced arm (= `current`).
- Dev gate: 2 dev drafts x `form` x 1 run: checker passes, every row answered, the annotated PDF
  builds. Not scored.

Gate `--five 0.50 --seven 0.80`. Cost ~72 x $2.7 = ~$195, judge ~$10. Claude returns to the
researcher if the projected total passes $250.

## Measures (fresh drafts)

Proposals are read from the final JSON block, as in W1, in every arm.

1. **Reference set.** Per draft, the proposals of all 9 runs are clustered by located span (overlap
   or within 1 line, W1's matching rule). Each cluster is judged once by Sonnet 5.5, no tools, arm
   hidden, skill vocabulary masked as in W1: `REAL` (a defect a careful copy editor at an ML venue
   would change: an error, or a clear clarity, consistency or framing problem) or `NOT` (taste, or
   not a defect). The judge prompt does not use the rubric's category names, so the criterion does
   not favour the arm that carries them. A 10% sample is judged a second time and the agreement is
   reported.
2. **Coverage (primary).** Per run: REAL clusters the run hits / REAL clusters in its draft. Mean over
   18 runs per arm.
3. **Stability (primary).** W1's pairwise proposal agreement across the 3 runs, averaged over drafts.
   Also reported: Jaccard of REAL clusters hit across run pairs, core share.
4. **Harm.** W1's precision judge on 15 sampled proposals per run: bad fix + meaning changed.
5. Reported: proposals per run by level, REAL share of each arm's proposals, coverage by judged
   category, checker result in the `form` runs, cost and time.

Guard measures on W1's drafts: W1's scorer and verdict procedure (plant recall, intensifier recall,
judged harmful of 270).

## Criteria

1. **Primary, coverage:** `form` - `current` >= **+0.10**.
2. **Primary, stability:** pairwise agreement, `form` - `current` >= **+0.05**.
3. **Guards:** W1 plant recall >= 0.881 (W2 reduced 0.931 - 0.05); intensifier >= 15/18; judged
   harmful <= 15 of 270 on W1's drafts; on fresh drafts judged harmful share `form` <= `current` +
   0.02; cost per run <= 1.3 x `current`.

| Outcome | What follows |
|---|---|
| both primaries and every guard met | merge `proofread-form`, measured line in SKILL.md |
| one primary met, guards met | report, decide with the researcher |
| neither primary met | report, no merge; read the traces for whether the form was filled honestly |
| a guard missed | read the traces before anything else, report |

`form` vs `without` and `current` vs `without` are reported with the same measures (secondary): the
series' first proofreading coverage numbers against the bare agent on unplanted drafts.

## Analysis notes

Paired by draft; per-draft differences reported, sign test (direction only). The reference set is
built from the arms being compared, so an arm that proposes more can hit more clusters; proposals
per run and the REAL share are reported beside coverage so a gain from volume alone is visible. The
`form` arm's checklist may also push proposals the judge calls `NOT`: that shows in the REAL share
and the harm guard. Scoring refuses to run before all 54 fresh runs have a JSON block and every
cluster has a verdict.

## Frozen material

To be added as amendment 1 before the first test run: variant commit, frozen copies, case hashes,
judge prompts and scorer hash.
