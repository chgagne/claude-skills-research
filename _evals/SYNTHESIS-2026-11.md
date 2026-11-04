# What the skill evaluations have shown so far (October to November 2026)

This summarises the with/without evaluations run since 2026-10-08. The details are in
`_evals/README.md`, each skill's `PROTOCOL-*.md` and `RESULTS-*.md`, and the dated journal in
`_evals/journal/`.

## How the skills were measured

Each protocol was written and committed before any run. The material was fresh: drafts and
bibliographies from after the model's training cutoff, disguised, and checked with a memory
probe. Usually the material carried a planted defect, sometimes real documented ones. Runs went
headless on Opus 5.5, with the skill and without it (the "bare" agent: same model, prompt and
tools). Hits were judged by content and arm-blind. Planted types were first calibrated on the
bare agent and kept only when it missed them sometimes.

## Results by skill

| Skill | Main result | What changed in the skill |
|---|---|---|
| verifying-bibliography | Planted page shifts: skill 1.00 = bare 1.00. Real errors on fresh bibliographies: reduced skill 0.83, full 0.89, bare 0.86. The gain is cost: about half the bare agent's per run | Reduced to "run the script, read the report" (D4); the given-name check raised to MAJOR (E2: 0.94) |
| surveying-literature | Four measurements of recall on hard missing references: +4.6 to +18 points over bare, never reproduced at the +15 bar. Search results crowd out references the bare agent would list from memory | v3.3 live: cheapest version, memory list required before searching |
| verifying-proofs | Planted single-step errors: skill 8/8 = bare 8/8 | Reduced without loss (P2). Lean 4 certification by default: certifies real findings, 0 of 23 false findings certified |
| comparing-papers | C1: +16.7 (p = 0.375) while its extractor computed nothing. C2: a budget list the agent must answer item by item gave **+33.3 over bare (p = 0.008)**, false issues 0.04 vs 0.12 per run | Budget extractor merged |
| reviewing-paper-sources | R1: bare agent found about 22 of 24 planted internal inconsistencies (prose vs table, claim vs far table, gain inside a reported spread). Subtler plants could not be built on real drafts | None; gain unmeasured |
| explaining-derivations, proofreading-paper-writing | Not measured | |

## The pattern

1. **On a single planted defect, the bare agent is usually at ceiling.** That held for
   bibliography page shifts, proof steps, misquoted comparison numbers and internal
   inconsistencies. With fresh material and a direct prompt, Opus 5.5 recomputes derived numbers,
   checks claims against tables and looks up references without being told to.
2. **Prose instructions are often not executed.** Asking the agent to attend to something new
   (a memory list, an optional Lean step, a closure check) was read and then not applied, in
   three separate tests.
3. **Structure the agent must answer is executed, and it is the only change that beat the bare
   agent on fresh material.** C2's budget list makes the agent answer each entry. It is also the
   cheapest change measured.
4. **Several skills could be cut down without loss.** The bibliography skill went to 81 lines and
   the proof skill to 86, with no loss on the cases they were tuned on (on fresh bibliographies the
   reduced version later missed its recall bar by one hit). What made a difference was a script or a list the
   agent had to answer.

## A different question: consistency rather than recall

Recall on planted defects was the wrong main measure for a review skill. A review without the
skill can be effective, but each run picks its own coverage, ordering and severity, and it
may skip a part. For a reviewing tool used repeatedly by a group, the useful property is a
standard, complete review that comes out the same way each time. Measuring the skill as a source
of variance reduction asks "does the review cover the same ground, reach the same findings and
the same verdict across runs?", not "does it find one more defect?".

The data already collected gives a first, post-hoc look (located-span agreement between pairs
of runs on the same case; small samples, not a protocol):

| Data | Arm | Issues per run | Pairwise agreement of findings | Plant outcome identical across runs |
|---|---|---|---|---|
| C2 (8 drafts x 3 runs) | budget list (structured) | 1.9 | **0.81** | **8/8 drafts** |
| | bare | 2.8 | 0.75 | 6/8 |
| | C1 skill (prose guidance) | 2.8 | 0.61 | 6/8 |
| C1 test (6 drafts x 3 runs) | skill | 6.1 | 0.71 | |
| | bare | 6.3 | 0.67 | |
| R1 (12 cases x 2 runs, full review) | bare | 25.5 (16 to 44 on one draft) | 0.63 | 11/12 |

Two readings, both preliminary:

- The structured version was also the most consistent one: every C2 pair got the same plant
  outcome in all three runs. The prose-guidance version was the *least* consistent, below the bare
  agent. So adding guidance to a skill does not by itself make runs more alike; adding structure
  might.
- A full review without the skill reaches about two thirds agreement between two runs, and its
  length varies by a factor of almost three on the same draft. That is the variability a
  standard review should remove.

## Proposed next protocol: R2, consistency of reviewing-paper-sources

Same material as R1 (disguised, probed drafts), no plants, no web tools, sibling modules off.

- **Arms:** current skill; bare; later possibly a structured version (a fixed checklist whose
  every item the review must answer: present / absent / not applicable, with the evidence).
- **Runs:** 4 per arm on 6 drafts (48 runs, about $60).
- **Measures, all within draft across runs:**
  1. Coverage: share of a fixed checklist (the skill's "Findings that recur" items, plus the
     template sections) that each review addresses. Report its mean and its spread.
  2. Finding stability: pairwise agreement of findings, and the share of findings that appear
     in at least 3 of 4 runs (the "core").
  3. Verdict stability: same recommendation and same top-3 concerns across runs.
  4. Guard: natural errors found (judged arm-blind) must not fall below bare.
- **Criterion (to be fixed in the protocol):** skill coverage spread and finding-stability
  better than bare by a margin set before the runs, with the guard met.

If the current skill is no more consistent than bare, the structured-checklist version is the
candidate change, in line with point 3 above.
