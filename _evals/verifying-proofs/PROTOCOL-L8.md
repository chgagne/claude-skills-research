# Protocol L8: discovery on the two unrun documented-defect papers

Written 2026-10-29, before any run. Next step 1 of the 2026-10-29 session close; the researcher
chose the scoring rules and the run count (one run per paper).

## Why

L5 left the "wrong verdict, then a certificate" path untested: model-written false findings are
refuted by the same model. Real withdrawn papers are the only material where a run can reach a
wrong verdict on its own. Two documented-defect papers from the local acceptance corpus survived
the L2 memory probe (`private/l2/probe/out/`, neither defect recalled) and were never run:

- **1101.2597** (optimal control of a hepatitis B model). arXiv v2: "withdrawn by the author due
  to a crucial error in one of equation in (3)". The source's `\label{eq3}` is the controlled
  state system (paper.tex lines 288-303).
- **0907.0453** ("Random DFAs are Efficiently PAC Learnable"). arXiv v2: "withdrawn due to an error
  found by Dana Angluin and Lev Reyzin". No location. One search (the Angluin, Eisenstat,
  Kontorovich, Reyzin TR-1421, Dec 2009, SQ lower bound for random DFAs under arbitrary
  distributions) does not name the faulty step. The probe caveat stands: one probe run had "a
  vague sense it may have been withdrawn", no location.

## Runs

The live skill at 4b56e5c (verifying-proofs + `_shared`), frozen into `private/l8/run/`. L4's
prompt, tools (no web), limits (100 turns, 40 min, $20 cap), Lean scaffold. Inputs are the v1
sources: 1101 as `paper.tex` (figures omitted); 0907 as `paper.tex` with its two style files
(theorem environments are defined there through macros such as `\bethn`) and its `.bbl`.
One run per paper, 2 runs. Launcher `private/l8/launch_l8.sh`.

## Measures and reading

- **1101.2597, hit:** a flagged entry located in eq3 that names a non-typographic error (for
  instance a term that makes the controlled system disagree with eq1 at u = 0). A typo-only flag
  in eq3 (letter case, stray comma) is not a hit. Read by content, not by span.
- **0907.0453, descriptive:** no hit or miss. Each flag is adjudicated by content as real, false
  or undetermined (a real verdict needs a counterexample or derivation I check, or a certificate
  that passes the fidelity check below). Reported: whether any flag bears on the main claim
  (learning under an arbitrary distribution, which the SQ lower bound contradicts).
- **Certificates, both papers:** every Lean file recompiled from the trace (heredocs, sed and
  Python edits replayed in order) and read for fidelity: does the Lean statement say what the
  paper says, with the paper's hypotheses? A certificate for a statement the paper does not make
  is the wrong-verdict-then-certificate failure this protocol looks for; each one is reported.
- Reported: other flags per run, cost, wall clock, Lean use.

## What follows

Discovery only, 2 runs: no SKILL.md change from this alone. A fidelity failure goes to the
researcher before any change to the Lean step. A 1101 miss: traces read before any rewording
(three times now, prose checklist lines were read and not applied).

## Budget

About $5 estimated; $40 cap.
