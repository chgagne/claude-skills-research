# Probe L1: can an agent with Lean 4 + Mathlib settle the plants the bare agent missed?

Written 2026-10-25, before any run. Chosen by the researcher after P1 ("probe the dev misses").
A feasibility probe, not a with/without comparison: it asks whether Lean can be part of the
method at all on this material.

## Material

The two tightened dev hypothesis plants the bare agent missed in 3 of 4 runs:

- **d2** (2607.06252, `lem: rn^q`): "for all f in F" weakened to "all measurable f with
  0 < Z_f < infinity"; false (concentration example in the plant file).
- **d3** (2607.25785, `lem:D`): the standing hypothesis `0 < G_s <= overline G_sigma` dropped;
  false (the bound grows like G_s^{2/3}, the coefficient like G_s^{8/3}).

## Procedure

Stage 1: one fresh agent (opus) per edited statement, not told that it was edited. It gets the
statement with the definitions it depends on (copied from the paper by Claude, no proofs), a Lean 4
+ Mathlib project (`~/Claude/lean-probe/probe`), and the task: decide whether the statement holds,
by formalizing it and proving it or its negation; 60-minute cap; report the Lean file, whether it
compiles without `sorry`, the verdict, and where the formal statement departs from the text.

Stage 2, only if stage 1 certifies at least one verdict: the same on the two original (unplanted)
statements, to see whether Lean also confirms or declines correctly on true lemmas.

## Measures

Per statement: verdict (holds / fails / undecided); Lean-certified (compiles, no `sorry`, no new
axioms); fidelity of the formal statement to the LaTeX, judged by Claude line by line; wall time and
tokens. Success for the probe: a certified, faithful refutation of at least one of the two.

## What it does not show

Two statements; no comparison with the bare agent's reading on the same budget. A success shows
Lean can be used on this material, not that it helps.
