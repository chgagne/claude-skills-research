# Protocol C3: an axis answer table to widen comparing-papers reviews

Written 2026-11-22, before the variant is built and before any C3 run. Direction chosen by the
researcher in an interview the same day (journal `2026-11-22.md`): "a required 'other differences'
section that a checker enforces, with the budget list kept", measured on C2's pairs, ~$80.

## Question

C2's budget list made the skill catch understated training budgets (21/24 vs 13/24 bare, p = 0.008)
but narrowed the reviews: 0.25 other real issues per run, against 0.58 bare and 0.83 for the
previous skill. The "answer each budget" step pulls the review onto budgets. **Does a table that
the review must answer for every axis, not only budgets, bring the other real issues back to the
bare agent's level, without losing the budget recall?**

## The variant (branch `compare-axes`, from main)

- `run-compare.py` adds an **Answers** section at the end of the report, also written to
  `comparison-answers.md`: one row per budget pair it listed, then one row per axis — results
  as quoted, metrics, data and splits, protocol (evaluation setup), seeds, checkpoint, compute —
  each with columns `draft says` / `competitor says` / `verdict` (matches / differs / not stated /
  not checkable) / `quote or section`, every verdict cell `TO ANSWER`.
- `assets/check-answers.py comparison-answers.md` fails while any cell still reads `TO ANSWER`,
  or a `differs` row lacks a quote from each side.
- SKILL.md: the budgets section stays; a short "Answer every axis" section says to fill the
  table before writing the review, run the checker until `OK`, and report every `differs` row as
  an issue. Nothing else changes.
- Built and tuned on C1 development pairs only (not C2's test pairs).

**Dev gate** (before any test run): 2 C1 dev pairs × 1 run, variant only. Gate: the table is
filled, the checker prints `OK` in both runs, and the planted budget is reported. Dev runs are not
scored.

## Material and arms

C2's 8 test pairs (c108, c115, c116, c135, c140, c148, c156, c161), cases, prompt, tools, network
grants, limits and contamination rule, unchanged. **All three arms run the same day**, 3 runs per
pair per arm = 72 runs:

| arm | what it is |
|---|---|
| `wide` | comparing-papers at `compare-axes`, frozen when the dev gate passes |
| `live` | comparing-papers as published (C2's merged skill), frozen at the same time |
| `without` | the same agent, no skill |

C2's own runs (fixed / current / without, 2026-11-01) are reported beside as a replication, not
scored.

## Measures

C2's scorer (`score_c2.py`, unchanged): locator on the plant span ± 3 lines, then a content check
(hit = names the planted budget and its direction). Every issue of the 72 runs, shuffled with the
arm hidden, is adjudicated with C2's adjudication prompt (`adj/prompt.md`, verbatim) by subagents
in batches: hit / real / false / judgement. Claude checks every "false" and every "hit" against
the sources, as in C2.

## Criteria (same-day arms)

1. **Primary, breadth:** other real issues per run, wide ≥ without − 0.10.
2. **Recall kept:** wide ≥ live − 2 (of 24), and wide − without ≥ +0.15.
3. **False issues:** per run, wide ≤ 1.5 × without (C2's bar).
4. **Cost:** per run, wide ≤ 1.3 × without (C2's bar).
5. **Mechanism:** `check-answers.py` OK on the saved answers file in ≥ 22 of 24 wide runs.

All met: merge `compare-axes` with a measured line. Primary met, something else missed: report,
the researcher decides. Primary not met: report, no merge. Reported, not scored: judgement calls
per run, issues per run, the per-axis distribution of wide's real issues.

## Cost

72 runs × ~$0.55 ≈ $40; dev ~$2; adjudication subagents ≈ $15. About $57 (ceiling $80).

## Amendment 1 (2026-11-22, dev gate, before any test run)

- **Dev round 1 (d564ba8): gate failed.** d3: the script could not resolve the arXiv id inside the sandbox
  (it resolves locally; transient, and every arm runs the same script, so not fixed); d7: table filled, the
  checker never run. SKILL.md names the checker by `~/.claude/skills/...`, which does not exist in the eval
  sandbox. Fix (6874764): the script prints the exact checker command with absolute paths after the report,
  and the answers file carries it in its header. Round-1 copies kept in `private/c3/run/wide_dev1_d564ba8`
  and `out/dev1`.
- **Dev round 2 (6874764): gate passed.** Both runs filled the table and ran the checker to `OK`; both
  reported the planted budget (d3 60 vs 275 epochs, d7 7K vs 25K samples); d3 also raised a protocol issue.
- Frozen: **wide = 6874764**, **live = main 5107b1b** (C2's merged skill), `_shared` = C2's frozen copy
  (unchanged since). Dev cases are C1's d3/d7 with the scaffold pointed at C2's `_shared`.
- **Criterion 5 is read from the trace** (the sandbox does not keep `comparison-answers.md`): a wide run
  counts when the output of its last `check-answers.py` call is `OK`. Script resolution failures
  ("could not resolve") are counted per arm and reported.
- Launcher `private/c3/launch.sh test` (gate 0.50/0.80; traces persisted after each case).
