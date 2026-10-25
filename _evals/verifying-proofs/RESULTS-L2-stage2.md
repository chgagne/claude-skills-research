# Protocol L2, stage 2: discovery at ceiling, and the Lean step was never used (2026-10-25)

Design: `PROTOCOL-L2.md`, stage 2 section (255dcb3). Scorer hash committed before the runs (journal).
12 runs, 15:45 to 16:01, no web, none contaminated. Scores: `results/L2-stage2-2026-10-25.json`.

| | Reduced skill (main 255dcb3) | Reduced + Lean step (lean-step 2e4f829) |
|---|---|---|
| Documented defects found | **6/6** | **6/6** |
| Other flags per run | 9.3 | 9.5 |
| Mean cost per run | $0.64 | $0.69 |
| Runs that invoked Lean | - | **0/6** |

Papers: 2505.02888 (withdrawn: Theorem 2 / Lemma 2), 0801.4243 (withdrawn: "U in Lemma 2 is not a
subspace"), 1905.10936 (Lemma 2's error bound, refuted by a published correction). The memory probe
had shown the model does not recall these defects.

**Reading.** Both arms found every documented defect, in two to three minutes per run: the reduced
skill's reading method reaches these errors without Lean, so discovery has no headroom here. The
Lean arm never compiled anything. Every run said so in its report ("the witnesses below are worked
out by hand and haven't been machine-checked"); most also skipped the optional hygiene script. The
step is written as optional, gated on "a finding will go to an author", and agents asked only to
check a paper do not take it. Stage 2 therefore says nothing about Lean's effect on discovery: an
optional step that is not taken has no effect.

Side result: the first measurement of the reduced skill on documented real defects, 6/6 (the old
script-centred measurement flagged 0 of 6 at MAJOR or above).
