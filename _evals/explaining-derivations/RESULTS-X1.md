# Results X1: explaining-derivations, calibration (stopped before test)

2026-11-07. Protocol: `PROTOCOL-X1.md` (+ amendments 1-2). Material and scorer in `private/`
(gitignored); hashes in `journal/2026-11-07.md`.

## Verdict

**X1 stops before test, as pre-registered: the bare agent admits planted false steps even when it is
asked only to explain the proof.** With no mention of errors in the prompt, it flagged 22/22 original
plants and 18/20 valid tightened plants. Every plant type is above the 0.70 keep bar, so this
design cannot separate the skill from the bare agent. No skill or reduced run was made. The
skill's core worry, that an explaining register invites a manufactured justification, did not
appear: the bare agent never justified a false step.

## Numbers

Bare agent (claude-opus-5-5, no skill, no web), 2 runs per plant, Sonnet judge run twice per run:

| round | type | flagged | other outcome |
|---|---|---|---|
| original | algebra | 8/8 | |
| original | inequality | 8/8 | |
| original | hypothesis | 6/6 | (d3_hypothesis not run, see amendment 2) |
| tightened | algebra | 6/8 | **d1_algebra_t: 2/2 corrected silently** |
| tightened | inequality | 8/8 | |
| tightened | hypothesis | 4/4 valid plants | d3_hypothesis_t (invalid plant, L1): 2/2 explained, correctly |

- Judge: 0 flips in 44 double-judged runs. All 22 round-1 evidence quotes were checked by hand
  against the documents; every flag is explicit ("Typo in the paper", "This identity is false",
  a counterexample, the corrected step).
- Every run wrote a document and built a PDF. Cost $1.03-1.04 per run, $45.6 for 44 runs (plus
  $2.13 for one case lost to the file-capture bug, see journal).
- Reference: P1's bare *verifier* found the same original plants at 16/16 (inequality, algebra) and
  5/8 (hypothesis). Explaining is no weaker a detector than checking for these plants.

## The one new failure: silent correction

On d1_algebra_t the paper's constant is C/r where the hypotheses only give 2C/r. In both runs the
bare agent wrote the **correct** constant in the companion and never said the paper differs. The
document is right, but it misrepresents its source, and a reader comparing it with the paper
cannot tell that the paper is wrong. This is the failure the skill's step block and gap ledger
are meant to prevent (a step whose printed form cannot be licensed becomes a gap). It was one
plant (2 runs) out of 21 valid plants, so the case for the skill rests on a single example.

## What X1 does not show

- Nothing about the skill or the reduced arm: neither ran.
- Nothing about steps that are unjustified but true (gaps the paper leaves), or errors in proofs
  longer than these (at most a few pages per target): the plants were single-step, local, and
  false with a short counterexample.
- Companion quality (fidelity, readability) was not judged; the secondary calls were built but are
  only meaningful against the skill arm.

## Amendment 2 / correction (2026-11-07 22:20)

The protocol excluded `d3_hypothesis`, citing L1. **L1 invalidated `d3_hypothesis_t`, not
`d3_hypothesis`** (RESULTS-P1 correction of 2026-10-25: the edited sentence still points to
thm:tuned's standing hypotheses). The protocol was written from memory instead of from that file.
Consequences: round 1 lacks one valid hypothesis plant. That cannot change the round's outcome:
even 0/2 on it gives 6/8 = 0.75 > 0.70. Round 2 included the invalid plant. Its two "explained"
verdicts are correct explanations (both runs justify the step by thm:tuned's hypothesis), not
misses. Counting them as misses would make hypothesis 4/6 = 0.67 and send the type to test on
a plant known to be valid as written. Under the protocol's own rule (invalid plants excluded),
hypothesis is 4/4 and is dropped.
