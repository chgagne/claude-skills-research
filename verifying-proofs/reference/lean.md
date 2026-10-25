# Certifying witnesses in Lean 4 + Mathlib

Optional, and **unmeasured as a with/without**: nothing shows yet that Lean finds an error a careful
reader misses. What it adds is a machine-checked witness to hand an author.

## What the one probe showed (probe L1, 2026-10-25)

Two dropped-hypothesis lemmas from post-cutoff math.OC/stat.ML papers, one opus agent each, the full
paper, no web, a 60-minute cap (`_evals/verifying-proofs/RESULTS-L1.md` in the source repository):

- a measure-theoretic counterexample (a likelihood ratio with no finite q-th moment under a Gaussian
  prior, for every q > 1) was proved in about 15 minutes and 4 compiles;
- an explicit research-level bound (a constant-propagation lemma, 223 lines of Lean) was proved in
  about 25 minutes and 7 compiles, at about 55 s per compile.

In both cases the agent's informal reasoning was already right. In the second, the agent's reading
of the statement exposed that an edit meant to drop a hypothesis had left it reachable through a
reference, which is the kind of fidelity question a formal statement forces you to answer.

## Setup

```sh
brew install elan-init              # or the elan installer from the Lean website
lake +leanprover-community/mathlib4:lean-toolchain new probe math
cd probe && lake exe cache get      # downloads prebuilt Mathlib, about 5 GB
lake env lean MyFile.lean           # first compile of a file importing Mathlib: ~25 s
```

Check a result with `#print axioms <theorem>` appended to the file: the three standard axioms only,
no `sorryAx`.

## Fidelity, the part a compiler does not check

A Lean theorem proves exactly its statement. Before reporting, read the formal statement against the
LaTeX and list every departure: a general space specialised to the reals, a parameter given a value,
a definition taken as a hypothesis (for example `1 <= Lambda` instead of its formula), a probabilistic
step left outside the formal statement. A specialisation is fine for a counterexample, which needs
one instance; it is not fine for a claim that a lemma holds.
