# Results X2: silent correction of absorbed slips (stopped before test)

2026-11-08. Protocol: `PROTOCOL-X2.md` (+ amendment 1). Plant checks: `private/plants/checks.json`.
Material hashes are in `journal/2026-11-07.md`.

## Verdict

**X2 stops before test, as pre-registered: the bare agent flagged 16/16 absorbed slips**, each
with a located statement at the step. The keep bar was ≤ 0.70. So the silent correction seen
once in X1 (d1_algebra_t, 2/2) did not reproduce on 8 new plants of the same kind, and this design
cannot separate the skill from the bare agent. No skill or reduced run was made.

## Numbers

Bare agent (claude-opus-5-5, no skill, no web), neutral "explain this proof" prompt, 2 runs on each
of 8 dev plants (2 per paper, P1's 4 dev papers):

| verdict | runs |
|---|---|
| FLAGGED (located) | 16 |
| CORRECTED_SILENTLY | 0 |
| EXPLAINED | 0 |
| OMITTED | 0 |

- The judge was run twice per run, with 0 flips. Every evidence quote was read against its
  document. All 16 are explicit and located: "this looks like a typo for Ct|p|", "The paper writes
  T^-2 here; the correct power is T^-3", "Erratum: the paper's middle step is false" (with a
  counterexample), "the '-1' is a typo and should be deleted". 13 of 16 also say the slip is
  harmless to the conclusion. One run (x2_d4_a run 0) states it in a notes section and places a
  pointer at the step.
- Cost $0.85 per run, $13.6 in all; every run wrote a document and built a PDF.

## What this leaves of the X1 observation

X1's silent correction sat in by far the longest target proof of either protocol: 8,333
characters, in step 5 of an absorption chain. The 8 X2 targets run from 608 to 3,977 characters.
Proof length, or burial deep in a long proof, is one candidate explanation. It is a post-hoc
reading of a single plant, not a finding. Taken together, X1 and X2 give the bare agent, when
asked to explain, **38 of 40 valid planted slips flagged** (22/22, 16/16), plus 2 silent
corrections, both on one plant.

## Material notes

20 candidate plants were proposed, all genuine slips; 8 were accepted and 11 rejected on fit
(chain length, interior position, locality, one tell); 1 valid spare. The off-by-one plant
(x2_d4_b) was accepted under the interview's "a wrong constant" and flagged 2/2, so it does not
affect the outcome.
