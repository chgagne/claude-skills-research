# Protocol L3 results: default Lean certification costs +17% and was used in every run (2026-10-25)

Protocol: `PROTOCOL-L3.md` (c71b284). Skill with the default Lean step (`lean-step`, b651504), the
three documented-defect papers of L2 stage 2, one run each, no web, none contaminated. Certificates
recompiled by Claude with `lean-certify.py`; kept in `lean/L3/`. Scores: `results/L3-2026-10-25.json`.

| | Reduced skill (L2 stage 2, 6 runs) | Default Lean step (L3, 3 runs) |
|---|---|---|
| Documented defects found | 6/6 | 3/3 |
| Runs that used Lean | 0/6 (step optional) | **3/3** |
| Certificates attempted | 0 | 7 (5, 1, 1) |
| CLEAN at the end of the run / on recompile | - | 7/7 / 7/7 (one fixed after a failed first audit) |
| Mean cost per run | $0.64 | **$0.75 (+17%)** |
| Wall time per run | 88-162 s | 135-203 s |
| Other flags per run | 9.3 | 9.3 |

## Fidelity of the 7 certificates (Claude, against the paper)

| Paper | Finding certified | Verdict |
|---|---|---|
| 2505.02888 | `lem:eps_collapse`: eps > eps* does not give the claimed drift bound (delta = 4; the paper allows any delta > 0) | faithful instance |
| 2505.02888 | `lem:omega_fisher`: squared norm not superadditive (scores a = 1, b = -1) | faithful instance |
| 2505.02888 | `thm:multi_beta`: pairwise complementarity (taken with equality) does not give the k-fold bound | faithful instance |
| 2505.02888 | `thm:bounded`: c <= Gamma and Omega <= Gamma do not give c + delta Omega <= Gamma | faithful instance |
| 2505.02888 | `thm:async_hetero`: D built from the paper's lambda_i (1 + beta_ij); one step falls below rho(D) | faithful instance |
| 0801.4243 | Section 3 theorem: "positive definite" (the abstract says semidefinite) makes the hypothesis unsatisfiable | **partial**: Lean proves det != 0 for n = k = 1; the step to "not flat" is by hand. Disclosed in the fidelity notes, but the report's headline says "certified in Lean" |
| 1905.10936 | `lemma:m_bound`: G^2/(1-mu) fails (d = 1, mu = 1/2, t = 1: 49/16 > 2), and G^2/(1-mu)^2 holds | faithful instance |

**Blocking condition** (an unfaithful certificate presented as a certificate): not met in the strict
sense, since the partial one lists what was done by hand; but its headline overstates. None of the
7 certificates targets the documented defect itself: each run found it, and certified other
false-step findings. The documented ones (the unbounded-growth theorem and its lemma in 2505.02888, a
set U that is not a subspace in 0801.4243, an error bound that fails for decreasing step sizes in
1905.10936) were reported with informal witnesses only.

## Reading

Making the step the default changes behaviour completely (0/6 to 3/3 runs) at a modest cost: +17%
per run here, with five certificates in the paper that had twenty flags. Discovery is unchanged
(the defects were found either way). What it buys is seven machine-checked counterexamples, six of
them faithful instances on the paper's own objects. One fix the skill needs before shipping: a
certificate that covers only part of the argument must be labelled "partially certified" in the
report itself, not only in the fidelity notes.
