# Certifying findings in Lean 4 + Mathlib

Optional. Measured as a **certifier**, not as a discoverer: on real findings Lean turns a correct
verdict into a checked artefact; nothing yet shows it finds an error a careful reader misses.

## What was measured

**Probe L1 (2026-10-25).** Two dropped-hypothesis lemmas from post-cutoff math.OC/stat.ML papers. A
measure-theoretic counterexample (a likelihood ratio with no finite q-th moment under a Gaussian
prior) was proved in about 15 minutes; an explicit constant-propagation bound in about 25. The second
agent's reading also exposed that an edit meant to drop a hypothesis had left it reachable through a
reference: writing a formal statement forces that question.

**Protocol L2, stage 1 (2026-10-25).** 12 findings drawn from 161 that agents raised on four real
papers, judged against the paper first (11 real, 1 false), then each given to a Lean agent with a
30-minute cap:

| Outcome | Count |
|---|---|
| Real finding, defect certified on the paper's objects | 9 of 11 |
| Real finding, only related content certifiable (both notation slips) | 2 of 11 |
| False finding certified | 0 of 1 (the paper's sentence was certified instead) |
| Time per finding | 1 to 7 minutes, 1 to 3 compiles |

Every agent's prose verdict already matched the judged truth. Certificates often abstract the paper
(quantities as scalars, a toy class, a reduction from expectations to integrals done by hand);
three of the nine did, and the fidelity list is what made them usable.

## Kinds of certificate that worked

- **Counterexample instance**: the paper's assumptions proved for a concrete instance (a Dirac or
  Gaussian measure, a box in R^d, an explicit function), then the step shown false there.
- **Bound that does not follow**: the paper's own intermediate bound taken as a hypothesis, and the
  claimed conclusion shown not to follow (for example O(tau log tau) where Theta(tau^2) is claimed).
- **Missing licence**: the premises as stated shown not to entail the conclusion (a value at one N
  does not bound a limsup), possibly with the repair certified beside it.
- **Refuting a wrong finding**: the paper's statement proved, so the finding is withdrawn.

## Setup

```sh
brew install elan-init              # or the elan installer from the Lean website
lake +leanprover-community/mathlib4:lean-toolchain new probe math
cd probe && lake exe cache get      # downloads prebuilt Mathlib, about 5 GB
lake env lean MyFile.lean           # a file importing Mathlib compiles in seconds to a minute
```

Then audit every certificate with `assets/lean-certify.py FILE --project <project>`: it appends
`#print axioms` for each theorem, and prints `CLEAN` only when the file compiles, uses no `sorry`
and depends on `propext`, `Classical.choice` and `Quot.sound` alone (exit 0; 1 otherwise; 2 when
Lean is unavailable).

## Fidelity, the part no compiler checks

A Lean theorem proves exactly its statement. Before reporting, read the formal statement against the
LaTeX and list every departure: a general space specialised to the reals, a parameter given a value,
a definition taken as a hypothesis, a step done by hand outside Lean. A specialisation is fine for a
counterexample, which needs one instance; it is not fine for a claim that a lemma holds.
