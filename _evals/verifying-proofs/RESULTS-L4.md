# Protocol L4 results (2026-10-26)

Protocol: `PROTOCOL-L4.md` (d795580, amendment 1 a555c44). Skill `lean-hyp` 0540286 (Lean step also
certifies missing assumptions a main result depends on). One run per paper, no web. Found/certified
scored by reading the flags against the protocol's per-paper statements, not by span. Certificates
recompiled by Claude with `lean-certify.py`; kept locally in `private/l2/d/l4certs/`.

## Part A: L3's three documented-defect papers

| | L3 (lean-step b651504) | L4 (lean-hyp 0540286) |
|---|---|---|
| Documented defect found (by content) | 2/3 (corrected) | 2/3 |
| Documented defect certified | 0/3 | **1/3** (2505.02888, `thm:diverge`) |
| Certificates (theorems) / CLEAN on recompile | 7 / 7 | 7 / 7 |
| Unfaithful certificate presented as one | 0 | 0 |
| Mean cost per run | $0.75 | **$0.84** (+12%; bar $0.98) |
| Wall time per run | 135-203 s | 131-260 s |

Per paper:

- **2505.02888.** `thm:diverge` is now the first finding of the report, filed as a main result that
  fails as stated, with a Lean counterexample: ‖C(t)‖ = Ω(m_t) = 0, Γ = δ = 1; every stated hypothesis
  holds (the threshold premise vacuously) and the norm stays bounded. Fidelity: scalar model of
  ‖C‖ and Ω(m_t); that Ω can satisfy (O1)-(O3) while the messages sent carry no information is
  argued, not formalised, and the report says so. Verdict: faithful instance. `lem:gamma_min` (the
  other documented defect) found, not certified (fifth-ranked or lower). Three more certificates as
  in L3 (`thm:bounded`, `lem:eps_collapse`, `lem:omega_fisher`).
- **0801.4243.** The documented defect (U not a subspace) is missed again: 0 of 8 runs over L2 stage
  2, L3 and L4. The one certificate (positive definite + flat is unsatisfiable) now goes through
  flatness directly instead of a determinant step done by hand: faithful instance for n = k = 1,
  fixing L3's partial certificate.
- **1905.10936.** Found and ranked first ("the most consequential one"), with a sharper argument than
  in L3 (the recursion factor (1-δ/2) r_t² can reach 1 when η_{t-1}/η_t > 1). Left **not certified**
  with the reason "a bound with different constants may still hold: a gap, not a counterexample".
  The new text allows this, and the abstention is honest, but the published correction (2003.04706)
  states that the bound *is* false for arbitrary step-size sequences, with counterexamples: a
  certificate was available and was not attempted. Two other certificates (`lemma:m_bound`, as in
  L3, and a false intermediate line in Corollary 1's proof).

**Reading against the protocol.** The first outcome holds: a documented defect certified (1 of the
2 found), cost within 1.3 x L3, no unfaithful certificate. The change moved the choice exactly where
L3 failed (the missing-assumption theorem became finding 1 and was certified). Its limit shows on
1905.10936: an agent that does not find a counterexample quickly falls back on "may still hold",
which the text accepts. One run per paper: a direction, not an estimate.

## Part B: long paper (2608.28582)

One run, 60-minute limit (amendment 1): **10 minutes, $3.30, 21 turns, no timeout.** Four findings
(two false steps, a wrong coefficient, a definition that does not match its use); none overturns a
main theorem. Two certificates, both in one file, CLEAN in the run after one fix (an ambiguous
`integral_const` name, fixed by the agent) and CLEAN on recompile:

- `stepA_false`: the bound |u_{k+1}(t)| <= t^{l-k} ||u_k||_{L1} fails for u_k = 1, t = 1/2 (a faithful
  specialised instance; `k` is left as an auto-bound implicit, harmless here since only (k+1) - k = 1
  is used).
- `stepB_false`: "1/4 > 1 is false", certifying that the stated β = 1/4 violates the definition's
  β > 1. Trivial, and the report says it certifies only the mismatch.

The missing-licence finding (W^{3,1}_0 defined with L³) was left uncertified with the reason "the
conclusion is very likely still true", as the new text asks. Reading: on this paper the step's cost
is bounded by the number of serious findings, not by the paper's length; the agent found few, so
the five-certificate worst case was not exercised. The run cost about twice a P2 run ($1.68), most
of it the reading of 32k words.

## Summary for the decision

Part A meets the protocol's first outcome on one run per paper; part B shows no cost blow-up on a
long paper. Open: the 1905.10936 abstention (a counterexample existed), and 0801.4243 (0/8 runs find
the documented defect; a discovery limit, not a Lean one).
