# Results W1: proofreading-paper-writing, with and without the skill

Protocol: `PROTOCOL-W1.md` (fd1eecb, material hash 415a24f6). 36 runs on 2026-11-05 (09:19-18:32,
usage-gate pauses), none failed, every final message carried a parsable JSON block, every quote
located. Skill invoked in 18/18 skill runs; subagents used in 2/18 (the workflow ran in one agent
otherwise). Scoring: `private/w1/score_w1.py score --verdicts verdicts.json`.

## Verdict

**Neither primary met; guard met.** The skill finds one more planted defect type than the bare
agent (intensifiers standing in for a table number, 0.94 vs 0.39) and nothing else; its proposals
are not more stable across runs (slightly less). It makes fewer proposals (70 vs 94 per run), fewer
of them harmful by the judge (10 vs 23 of 270 sampled), and costs less ($2.60 vs $3.03).

## Arms

| arm | what it is |
|---|---|
| skill | proofreading-paper-writing at 21831f0, style defaults only (no profiles, no calibration round), deliverable prompt |
| without | same agent, same tools including subagents, same prompt, no skill |

## Results (6 drafts x 3 runs per arm; 29 plants)

| measure | skill | without | criterion |
|---|---|---|---|
| plant recall | **0.943** | 0.851 | skill - without >= +0.15: **+0.092, not met** (McNemar 10 vs 2, exact p = 0.04) |
| recall, intensifier (18 plant-runs per arm) | 0.94 | 0.39 | reported |
| recall, duplicate | 0.94 | 1.00 | reported |
| recall, term | 0.83 | 0.89 | reported |
| recall, subject-verb agreement and undefined acronym | 1.00, 1.00 | 1.00, 1.00 | reported |
| pairwise proposal agreement across runs | 0.817 | 0.849 | skill - without >= +0.10: **-0.032, not met** (lower in 5/6 drafts) |
| core share (proposal in all 3 runs) | 0.52 | 0.58 | reported |
| scripted harm share | 0.054 | 0.065 | skill <= without + 0.02: **met** (see caveat) |
| judged precision, 15 per run (Sonnet, arm hidden) | good 0.585, not a defect 0.378, bad fix 0.019, meaning changed 0.019 | good 0.622, not a defect 0.293, bad fix 0.041, meaning changed 0.044 | reported |
| proposals per run | 69.9 (35-113) | 93.6 (53-145) | reported |
| levels (mechanics / style / flow / framing, all runs) | 598 / 417 / 84 / 159 | 732 / 485 / 135 / 332 | reported |
| cost, time per run | $2.60, 8.0 min | $3.03, 10.1 min | skill <= 3 x without: met (0.86 x) |

## Reading

- The bare agent is at ceiling on every mechanical and terminology plant, as in R1 and P1. The one
  type it misses is the vague intensifier where a table holds the number: the skill's rubric names
  exactly that ("an intensifier where the number should speak"), and the skill arm acts on it in
  17/18 runs. That plant type was taken from the skill's own rubric, so it favours the skill by
  construction; the gain is real but narrow.
- Stability does not improve. Both arms agree at about 0.8 under the 1-line span rule (inflated by
  long single-line paragraphs in some drafts, equally in both arms). The skill's per-paragraph caps
  cut proposals by a quarter, which removes mostly framing/flow comments, but the remaining set is
  not more reproducible.
- The judge sees the skill arm make fewer harmful edits (10 vs 23 bad fix or meaning changed in 270)
  and more taste-level ones (0.38 vs 0.29 "not a defect"). Single judge, one pass: direction only.

## Sensitivity and caveats

- Strict span rule. By content, one more skill hit (177 duplicate, skill run 2: the quote occurs
  twice and the locator picked the first copy at line 581; its reason quotes "to to construct"):
  skill 0.954, +0.103. Several runs in both arms named "codebook" inside a paragraph-level naming
  finding anchored at the definition, not at the plant (134 term): counted as misses in both arms.
  Neither changes a criterion.
- Verdicts: a keyword prefilter chose the rows read by content; it first dropped duplicate findings
  quoted from the second copy across a line break (17 rows, both arms), caught by a search of every
  missed plant-run and restored before scoring. Proposals present only in the final prose and not in
  the JSON block do not count (protocol).
- The scripted harm check is mostly noise: of a sample of flags, most are thousands separators,
  numbers spelled out, or "5.70M" -> "5.7M"; one changes a number (100B -> 107B). The judged
  precision is the better harm measure here.
- Configuration: no style profiles and no calibration round (headless). The skill's main design
  claim, phrasing fixes in the author's own voice after calibration, is not measured.

## Outcome

Outcome table row "neither primary met, guard met": reduce the skill to what the trace shows the
agent used (as P2, D4) and validate non-inferiority. That is a direction for the researcher; not
started.
