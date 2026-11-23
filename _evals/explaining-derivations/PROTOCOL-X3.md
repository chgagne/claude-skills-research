# Protocol X3: a reduced explaining-derivations SKILL.md (non-inferiority to the live skill)

Written 2026-11-22, before the variant is built. Chosen by the researcher in an interview the same day
(journal `2026-11-22.md`, "Decision record: X3"): reduction, ~$80.

## Question

X1 and X2 stopped at calibration: asked only to explain a proof, the bare agent flagged 38 of 40
planted slips, so the skill was never run on this bench. Its SKILL.md is 316 lines, of which about 130
are development history (three dispatch runs, expander agreement, the measured-result narrative).
**Can SKILL.md be cut to about 170 lines, with the history moved to `reference/`, without changing what
the companion documents flag or how often they are built, and without raising cost?** This is also the
first time the skill itself is run on planted material.

## The variant (branch `explain-lean`, from main)

- SKILL.md keeps: overview and thesis, Run it, the three-phase workflow, the step block, the closed
  licence set, the gap ledger, failure is a result, the four coherence guards, latexmk absent, limits.
  Each shortened where it repeats itself.
- Moved word for word to `reference/development-history.md`: "What the first real run cost", "The second
  run, on a public paper", "The third run…", "Do two expanders find the same gaps?", and the "Measured
  results" narrative (SKILL.md keeps one line per measured result).
- Untouched: `assets/`, the other reference files. Target ≤ 180 lines. Frozen before any test run.

## Material and arms

X2's 8 absorbed-slip cases (P1's 4 dev papers, 2 plants each), X2's prompt, tools (Read, Write, Edit,
Bash, Glob, Grep, Skill, Agent; no web), limits and file capture, unchanged. Arms **lean** and **live**
(main, frozen at the same time), **run the same day**, 2 runs per case = 32 runs. No new bare runs: X2's
16 bare runs (16/16 flagged, $0.85 per run, 2026-11-08) are reported as context, not compared.

**Dev gate** (before the test): one live and one lean run on an X1 case not in the test set
(`d2_algebra`). Gate: both runs write a companion document and invoke the skill. The live run's cost
sets the expected spend; if it is above $2.5, the test drops to 1 run per case (16 runs) and amendment
1 says so.

## Measures

X2's judge (`judge_x2.sh`, prompts from `score_x2.py`, unchanged; Sonnet, double-judged with a
tie-break): the plant verdict (FLAGGED / CORRECTED_SILENTLY / EXPLAINED / OMITTED) and the other gaps
the document raises, each REAL or FALSE against the original paper. From the captured files: whether a
PDF was built for the target, and whether `run-explain.py` ran and a subagent was dispatched.

## Criteria (same-day arms)

1. Plant flagged: lean ≥ live − 2 (of 16).
2. FALSE other gaps per run: lean ≤ 1.5 × live (≤ 0.5 if live is 0).
3. Document built (PDF for the target): lean ≥ live − 1.
4. Cost per run: lean ≤ live.

All met: merge `explain-lean` with a measured line. Otherwise: report, the researcher decides. Reported,
not scored: REAL other gaps per run, silent corrections, skill pipeline use (plan / dispatch / assemble),
pages, and the live skill against X2's bare numbers (different days, context only).

## Cost

Unknown per skill run (never measured). If ~$2: 32 runs ≈ $64, dev ≈ $4, judge ≈ $3; ≈ $71.

## Amendment 1 (2026-11-22, dev gate, before any test run)

- Variant frozen at **9c7b663** (branch `explain-lean`): SKILL.md 316 → **180 lines**; the four history
  sections and the measured narrative moved word for word to `reference/development-history.md`, plus the
  passages shortened in place (kept verbatim at the end of that file). 126 tests pass. Live = main 2d980c0.
- **Dev gate passed**: live and lean on X1's `d2_algebra` both invoked the skill and wrote and built a
  companion ($1.25 and $1.24). Test at **2 runs per case** (32 runs).
- Observed: **neither dev run used the pipeline** (`run-explain.py` plan, dispatch, assemble); both
  wrote the companion directly under `companion/`, as the prompt asks. The test therefore measures what
  the SKILL.md text changes in a hand-written companion. Pipeline use is reported per run.
- Scorer `private/x3/score_x3.py` (score_x2 unchanged, x3 paths, arm = output dir, frozen skill path
  masked before X1's contamination rule); judge `private/x3/judge.sh` (judge_x2.sh, dir switched).
