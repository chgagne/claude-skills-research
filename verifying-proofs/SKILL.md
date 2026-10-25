---
name: verifying-proofs
description: Use when checking the mathematics of a paper rather than its claims — verifying a theorem's proof, an algebraic derivation, a bound, or an appendix full of lemmas. Triggers on "check this proof", "verify the derivation", "is Lemma 3 correct", "does the algebra work", a paper directory containing theorem/proof environments, or a referee asking whether a mathematical argument holds.
---

# Verifying Proofs

**You are the checker.** Measured against the same agent without this skill, careful reading
found planted inequality, algebra and dropped-hypothesis errors as often as the skill did, and
real slips in unplanted papers at the same rate. What this skill adds is a method for the reading,
a hygiene script, and rules that keep reports honest.

## Read every load-bearing proof

The proofs the contribution rests on, not all of them. For each:

1. **Every displayed chain, one relation at a time.** Each `=`, `\le`, `<` must follow from the
   line before it plus something stated. Middle relations of long chains are where slips hide:
   a lost factor, a constant halved, a square dropped, `\le` where only `\ge` holds.
2. **Every hypothesis of the statement: where is it used?** Find the step that needs it. Then the
   reverse: for every step that needs a condition (a sign, a range, a vanishing trace, a
   positivity, a "for all large N"), find where it was assumed. A condition used but never stated,
   or stated in the main text and lost in the appendix restatement, is the most common real
   defect. Work `reference/structural-audit.md` (hypothesis use, quantifier order, induction
   coverage, inequality direction).
3. **Every cited result: are its hypotheses met where it is applied?** A theorem applied at one
   width when it needs all large widths, or at `\beta \ne 0` when it needs `\beta > 0`.

**Back each finding with a witness.** A counterexample with concrete values satisfying every stated
hypothesis, or the one-line derivation of the correct form. For polynomial arithmetic, a short Z3
or SymPy script settles it; write the values into the report.

## Certify the witness in Lean (optional, unmeasured)

When a finding will go to an author and a Lean 4 + Mathlib project is available (`lake env lean`
works in it), certify the witness: state the counterexample, or the corrected inequality, as a Lean
theorem and prove it. Report the file, `#print axioms` (only `propext`, `Classical.choice`,
`Quot.sound`; no `sorry`), and every place the formal statement departs from the LaTeX, since a
faithful-looking specialisation is the usual way a Lean proof says less than it seems. Cap it at
about 30 minutes per finding; if it does not close, report the finding with its informal witness and
say the Lean attempt did not finish. Never install Lean on your own; ask. Setup and what the one
probe showed: `reference/lean.md`.

## Run the hygiene pass

```sh
python3 ~/.claude/skills/verifying-proofs/assets/run-proofcheck.py main.tex --out review-assets/
```

Stdlib only; SymPy and Z3 optional. It finds what is mechanical: a claim dependency cycle, an
induction with no base case, a restatement whose hypotheses differ from the body version, a division
by something never shown non-zero. It does **not** check whether the mathematics is right: on six
papers with documented proof errors it flagged none. Use `--emit-symbols-template` first on a long
paper (it lists symbols whose domain the paper never states), `--claims thm:main` to restrict.
Exit code `2` means degraded coverage; say so. The full option list, the scripted engines and the
two-translation protocol for agent-written check scripts are in `reference/design-notes.md`.

## Report

For each finding: a verbatim quote of the step, the claim it belongs to, what is wrong, the
witness. Then say what it does to the result:

- **the step is false** — and whether the result survives (the false step's conclusion may only be
  used where it still holds). A false step is a claim about the step, not the theorem;
- **the licence is missing** — the step may be true but a condition it needs is nowhere assumed;
- **cannot check** — measure-theoretic or asymptotic reasoning with no stated bound. A finding,
  not a pass.

**Never report a counterexample at a point the paper excludes.** A symbol whose domain the paper
never stated cannot refute a step; ask, or say the domain is missing. Read domains where the step
is, not where the letter first appeared: long documents reuse letters.

## Limits

- Nothing here certifies a proof; a clean read is "no error found", never "the proofs are correct".
- Proofs written as running prose, outside `\begin{proof}`, are invisible to the script.
- `reference/false-alarms.md` lists every way the script has been wrong so far; read it before
  trusting a script finding on an unusual notation.

## Measured

- **Against the bare agent** (protocol P1, 2026-10-24, no web tools): on fresh math.OC/stat.ML
  papers with one planted error, the bare agent found inequality slips 8/8 and algebra slips 6/8
  even when made subtler; on four dropped-hypothesis test cases skill and bare agent both found
  8/8, at the same cost. Every sampled extra flag was a real slip in the original paper.
  This shorter text did as well as the full one on the same cases (P2: 8/8, $1.68 per run).
- **The script** (seeded benchmark, `assets/tests/test_seeded_errors.py`): 6/6 seeded hygiene
  defects, 0 false alarms on the correct originals; on 13 real papers, 0 fabricated `CRITICAL`.
  With a translated check script it exactly refuted the faulty step of Adam's convergence proof
  (arXiv:1804.10587). Details in `reference/design-notes.md`.

## See also

- `reference/structural-audit.md` — the reading checklist, and what each failure looks like
- `reference/design-notes.md` — the script's options, engines, severity ladder and measurements
- `reference/lean.md` — Lean 4 + Mathlib setup for certifying witnesses, and the probe behind it
- `reference/engines.md`, `reference/step-ledger.md`, `reference/false-alarms.md`
- `explaining-derivations` — expands a proof step by step; `reviewing-paper-sources` invokes this
  skill in phase 4
