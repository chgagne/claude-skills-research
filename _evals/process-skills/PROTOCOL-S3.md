# Protocol S3: reduced process skills (non-inferiority on the S1/S2 scenarios)

Written 2026-11-26, before any skill is cut. Chosen by the researcher in an interview the same day (journal
`2026-11-26.md`).

## Question

S1 and S2 showed that the bare agent already makes most of the right calls, and that the process skills
matter where they load and the bare agent errs (r5: ask before changing what the arms compare). Each skill is
about 400 lines. **Can each be cut to about half, keeping the rules that change decisions in SKILL.md and moving
the cases and general advice word for word to `reference/`, without losing decisions or loading?** This is the
same pattern as R6 and X3.

## The variant (branch `process-lean`, from main)

For each of running-cluster-experiments, using-drac-clusters and collaborating-on-research:

- `description:` unchanged (S2's text), so the loading behaviour is not what changes.
- SKILL.md keeps: overview, every rule stated as a rule (one or two lines each), the commands, the red flags
  and the "common mistakes" lists as one line per item. Target ≤ 220 lines.
- Moved word for word to `reference/` in the same skill: worked examples, incident narratives ("on one
  campaign…"), measured tables, long explanations. SKILL.md points to each file in one line where the text
  used to be.
- Not changed: rules themselves (no rewording that changes meaning), assets, scripts, other reference files.
  The b8 conventions ("UNVERIFIED", decisions filed in CLAUDE.md) stay as they are: S3 tests cutting, not
  changing behaviour.
- A sentence-level check against the old SKILL.md finds no sentence absent from SKILL.md + reference files
  except paraphrases kept in SKILL.md. Frozen before any run.

## Material and arms

S2's 21 scenarios (S1's 16 + the 5 drac copies with real names), cases, prompt, tools and judge, unchanged.
**All arms run the same day**, 3 runs each:

| arm | what it is | runs |
|---|---|---|
| `lean` | the scenario's target skill from `process-lean` | 63 |
| `live` | the scenario's target skill as published (S2's merged text) | 63 |
| `without` | no skill (on S1's 16 scenarios only, for context) | 48 |

174 runs. Judged as in S2 (arm hidden, double-judged with a tie-break).

## Criteria (lean vs live, same day)

1. Pass rate: lean ≥ live − 3 (of 63).
2. Load rate: lean ≥ live − 3 (of 63).
3. r5 (ask before syncing): lean ≥ live − 1 (of 3).
4. Cost per run: lean ≤ live.

Each criterion is also reported per skill. All met: merge `process-lean` with a measured line per skill.
Otherwise: report, the researcher decides. At 3 runs per arm, a per-skill or per-scenario difference of one
or two runs is noise (S1's r3 did not replicate); only the pooled criteria decide.

## Cost

174 runs at ~$0.13 ≈ $23; judge ≈ $5; the three cuts are done by subagents (≈ $5).

## Amendment 1 (2026-11-26, variant built, before any run)

- Variant frozen at **f66b067** (branch `process-lean`); live = main f8ad8a4 (S2's descriptions). Cuts made by
  three subagents, one per skill, then checked by Claude.
- Size, lines and bytes: running-cluster-experiments 418 → 218 lines, 25.1 → 16.5 KB (65%);
  using-drac-clusters 392 → 220, 20.9 → 11.9 KB (57%); collaborating-on-research 413 → 217, 22.0 → 15.4 KB
  (70%). **The line counts overstate the cut**: about half of each line reduction came from joining wrapped lines
  and paragraphs. The byte figures are what the agent actually reads less of.
- Checks: frontmatter byte-identical to main in all three; sentence check 0 / 0 / 3 missing (the 3 are
  sentences split by a heading, present verbatim in `reference/why.md`); a cross-contamination probe found
  only cross-references already in the originals. The subagents shared the scratchpad and one saw its temp
  files overwritten by a sibling; it rebuilt from git, and the checks above show no file holds another skill's text.
  using-drac-clusters assets tests: 339 passed.
- Run material `private/s3/` (S2's 21 scenarios linked), launcher, scorer `score_s3.py`, S2's judge.
