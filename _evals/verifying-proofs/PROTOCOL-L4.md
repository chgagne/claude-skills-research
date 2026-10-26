# Protocol L4: certifying the defect that matters, and the cost on a long paper

Written 2026-10-26, before any run. Design chosen by the researcher the same day (journal
2026-10-26): extend the Lean step to missing assumptions a main result depends on; measure on L3's
papers and on one long paper first; the false-certification check (thread 3) is a later protocol,
written after this one is read.

## Why

L3 produced 7 clean certificates, none on a documented defect. Re-reading the runs (correction notes
in RESULTS-L2-stage2 and RESULTS-L3): in 2505.02888 and 1905.10936 the documented defect was filed as
a *missing assumption*, a class the step did not cover; in 0801.4243 no run found the documented
defect at all (span hits were a typo). The skill on branch `lean-hyp` (0540286) adds "missing
assumption that a main result depends on" to the certifiable classes, most consequential first.

## Arm and material

The skill at `lean-hyp` 0540286, frozen into `private/l2/d/run/lean4/`. Same prompt, tools (no web),
scaffold (toolchain and clean Mathlib project cloned into the run's HOME) as L3.

- **Part A.** L3's three papers, one run each; limits as L3 (100 turns, 40 minutes, $20 cap).
- **Part B.** One long paper: 2608.28582 (P1 dev paper, original text with no plant, ~32k words, 77
  proof environments); one run; 200 turns, 180 minutes, $30 cap (five certificates at up to 30
  minutes each, plus the reading).

## Measures

Per run: wall time, cost, turns, timeouts; certificates attempted, `CLEAN` on recompile by Claude,
and for each clean certificate a fidelity verdict (faithful / partial / unfaithful) and whether the
report labels it accordingly.

**Part A, by reading the flags, not by span.** A documented defect is *found* when a flag states it:

| Paper | Found when a flag says |
|---|---|
| 2505.02888 | Theorem 2 (`thm:diverge`) does not follow because crossing the threshold is never established, or Lemma 2 (`lem:gamma_min`) is false (compression can expand / Omega_cg can be 0) |
| 0801.4243 | the set U in Lemma 2's proof is not a linear subspace (not closed under addition), or an argument that needs U to be one fails |
| 1905.10936 | the error bound (Lemma 2 / `lemma:error_bound`) is established only for a constant step size and is used for non-constant or decreasing ones |

It is *certified* when a clean certificate is a faithful or partial instance of that statement (for a
missing assumption: an instance meeting every stated hypothesis where the conclusion fails).

## Reading (no automatic decision)

Reported to the researcher, who decides on merging `lean-hyp`. What each outcome suggests:

- A documented defect certified in at least one of 2505.02888 / 1905.10936, cost per run at most
  1.3 x L3's $0.75, no unfaithful certificate presented as one: the extension does what it was for;
  merge, then thread 3.
- Found but filed as "not certified: conclusion may still hold": legitimate under the new text if
  the reason is right (checked by Claude); reported as such, not as a failure.
- Same behaviour as L3 (other findings certified, documented ones not attempted): the wording does
  not move the choice; diagnose with the researcher before any rewording.
- **Blocking regardless:** a clean certificate presented as certifying a finding when its statement
  does not.

0801.4243 is a discovery measurement (missed in all 7 earlier runs); it is reported, not scored for
certification. Part B is reported as is: time, cost, number of certificates, any timeout. With one
run per paper, every number here is a direction, not an estimate.

## Budget

Part A about $3, part B about $5 to $15. Gate as usual (5h <= 0.40, 7d <= 0.75).

## Amendment 1 (2026-10-26, before part B ran)

The eval harness rejects `timeout_seconds` above 3600, so part B's case failed to load (no run, no
cost). Part B's limit becomes **60 minutes** (harness maximum), 200 turns, $30 cap. A timeout is
reported as such, with how many certificates were attempted and closed by then; it answers the
cost question in the negative direction (five certificates do not fit in an hour on a long paper).
