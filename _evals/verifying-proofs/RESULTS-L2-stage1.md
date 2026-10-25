# Protocol L2, stage 1: Lean certifies most real findings; rule says develop (2026-10-25)

Protocol: `PROTOCOL-L2.md` (94006dd). Draw and ground truth committed by hash before any Lean run
(journal 7c4bdfc); fidelity tiers fixed after 3 of 12 reports and before the other 9 (journal).
12 opus agents, one per claim, Lean 4.36.0-rc1 + Mathlib, 30-minute cap, no web. Every file
recompiled by Claude: no `sorry`, only `propext`, `Classical.choice`, `Quot.sound`. Files in
`lean/L2/`; per-claim notes in `results/L2-stage1-2026-10-25.json`.

## Material

161 unplanted flags from P1/P2 runs on 4 post-cutoff papers, 32 distinct claims after
deduplication, 12 drawn (seed 20261025). Ground truth (Claude, before Lean): 11 real, 1 false.

## Result

| Claim | Truth | Defect | Lean tier | Minutes |
|---|---|---|---|---|
| 0 | real | intro claims O(2^d), theorem gives poly(2^d) | A | 5 |
| 4 | real | theorem applied at one width, needs all large widths | A (abstract) | 1 |
| 6 | real | box tube bounded as if Euclidean (sqrt d for d) | A | 1 |
| 10 | real | outer expectation over y, should be x (notation) | B | 4 |
| 11 | real | space named Phi_F, defined as F_Phi (typo) | B | 3 |
| 17 | real | change of measure divides by the wrong normaliser | A (reduction by hand) | 5 |
| 19 | real | derivative missing a minus sign | A | 5 |
| 22 | real | lemma applied to bracket endpoints outside F | A (toy) | 6 |
| 24 | real | side remark claims Theta(tau^2), sum is O(tau log tau) | A | 5 |
| 28 | real | beta = 1/4 written for 5/4 | A | 5 |
| 30 | real | Sobolev space defined with L^3, needs L^1 | A | 7 |
| 31 | **false** | flag says the cited cutoff is too weak | **flag refuted** (paper's sentence certified) | 5 |

A: the defect certified on the paper's objects (or, for a licence gap, the stated premises shown not
to entail the conclusion). B: related formal content certified, not the defect. 

**Decision rule (researcher's choice): met.** Real flags certified at tier A: 9/11 = 82% (bar 50%).
False flags certified: 0/1 (bar 0), and Lean certified the opposite. Sensitivity: dropping the three
weaker A certificates (abstract, toy, reduction by hand) gives 6/11 = 55%, still above the bar. The
two B are notation slips with no formal content.

## What it does and does not show

- Lean certification of real findings in research papers is **fast and cheap**: 1 to 7 minutes,
  1 to 3 compiles, about 40 to 60 thousand agent tokens per claim, far inside the 30-minute cap.
- **Every Lean agent's prose verdict matched the ground truth (12/12)**, the false flag included.
  Lean never changed a verdict here; it turned a correct verdict into a checked artefact, and in
  claim 31 it made the refutation of a wrong flag precise.
- The "no false certification" condition rests on one false flag. The material had few false flags
  to draw from (P1's other flags were mostly real).
- Certificates often abstract the paper (scalars for quantities, a toy class, a hand reduction);
  the fidelity list each agent writes is what makes a certificate usable, and it has to be read.
- This is certification, not discovery. Stage 2 (D) asks the discovery question.
