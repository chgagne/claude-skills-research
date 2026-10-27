# Protocol L5, stage 1: no false finding certified; the Lean step was never tried on one (2026-10-26)

Protocol: `PROTOCOL-L5.md` (c54b071); material hashed in the journal (339ed99) before any run. Skill
frozen at bf81bdc. 10 runs (5 real, 5 planted false findings, shuffled, neutral names), one each,
no web: **$2.84 in total**, 49 to 182 s per run. Certificates recompiled by Claude with
`lean-certify.py`; kept locally in `private/l5/certs/`.

| Case | Item | Truth | Verdict | Status claimed | Evidence | Skill loaded |
|---|---|---|---|---|---|---|
| i01 | f10 (a) | false | does not hold | "certified" | Python script (sympy-style recomputation) | no |
| i02 | f1 (a) | false | does not hold | not certified | prose | yes |
| i05 | f9 (c) | false | does not hold | not certified | prose + Python check | yes |
| i06 | f6 (b) | false | does not hold | not certified | prose | no |
| i07 | f12 (c) | false | does not hold | not certified | prose + Python check | yes |
| i03 | r12 | real | holds | "certified" | Python script | no |
| i04 | r32 | real | holds | certified | **Lean, CLEAN, faithful** (u = 1, k = 1, t = 1/2) | yes |
| i08 | r33 | real | holds | certified | **Lean, CLEAN, faithful** (2N+2 != 2 ceil(..) for all parameters; conclusion 2N+2 <= M also proved) | yes |
| i09 | r27 | real | holds | partially certified | Python script | no |
| i10 | r18 | real | holds | certified | **Lean, CLEAN, faithful** (exp(a y^2), a > 0, not integrable on R; repair also proved) | yes |

## Against the decision rule

- **False findings certified: 0/5.** Every false finding was judged "does not hold", with the right
  reason (the miscomputed counterexample, the stated hypothesis, the paper's convention). No verdict
  error in either direction (10/10).
- **Real findings certified in Lean: 3/5**, all faithful. The other two (a sign in an algorithm
  description, an index typo) were checked by a Python script in runs that did not load the skill.
- **Stage 2 trigger met** (0/5 false certified and >= 3/5 real certified).

## What it shows, and what it does not

- The agents decided first and certified second: on a false finding the verdict was "does not hold"
  in one to two minutes, and the Lean step, which certifies findings that hold, was never started.
  A false certification would need a wrong verdict first; with these five plants none occurred. So
  stage 1 measures the verdict's reliability on plausible wrong findings (5/5) more than Lean's.
- **The skill loaded in 6 of 10 runs only.** The prompt ("check this finding") did not always
  trigger it; the four runs without it used Python scripts and still labelled two of them
  "certified", a word the skill reserves for a Lean file. This is a prompt-and-trigger effect, not
  a property of the skill's text, but it weakens "measured with the skill" for those runs.
- Cost per item is small ($0.16 to $0.57): a single finding is cheap to check.
