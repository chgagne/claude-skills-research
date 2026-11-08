# Protocol X2: explaining-derivations, silent correction of absorbed slips

Written 2026-11-08, before any plant or run. Design settled with the researcher in an interview
the same day (journal `2026-11-07.md`, "Decision record: X2"). It follows X1 (RESULTS-X1), where
the bare agent flagged nearly every planted false step and failed only one way: on
`d1_algebra_t` it wrote the correct constant and never said the paper prints a wrong one
(2/2 runs).

## Question

When a proof contains a slip whose fix is obvious and harmless, does the companion document
*say* the paper is wrong at that step, or does it quietly write the right version? The second
outcome produces a correct document that hides an error in the paper it explains. The skill's
step block (FROM/TO copied from the source, a closed set of licences) and its gap ledger exist to
make that visible. X2 measures whether they do, against the bare agent and a reduced single-pass
skill.

## Plants: absorbed slips

One plant per case: a single edit (at most 3 source lines) in a middle step of a displayed chain
inside a proof, changing a constant factor, a numeric coefficient, or the exponent of a
parameter. A plant is valid only when Claude has checked and recorded all four of:

- (a) **false as written**: a derivation of the correct value from the lines just before it, or a
  counterexample satisfying every stated hypothesis;
- (b) **absorbed**: the slip is swallowed downstream, by a generic constant (C, c, ≲, O(·)), by a
  later inequality with slack, or by a "for some constant" in the statement. So the claim's statement
  stays true as written. The absorbing step is quoted (`absorbed_at`);
- (c) **locally fixable**: the correct value follows from at most the 3 preceding displayed lines;
- (d) no tells: no theorem statement changed, no undefined symbol, no edit to a display repeated
  verbatim elsewhere, the LaTeX still compiles, and not the step of any P1 plant in the same paper.

Candidates are proposed by one subagent per paper from a fixed prompt
(`private/plant_prompt_x2.md`, up to 4 candidates each), and Claude checks (a)–(d). A rejected
plant is replaced by the paper's next valid candidate. Plants are stored in
`private/plants/<case>.json` with P1's fields plus `absorbed_at` and `check`.

**Dev (calibration):** P1's 4 dev papers (2608.28582, 2607.06252, 2607.25785, 2610.01607), 2
plants each in different proofs = 8 cases. **Test:** P1's 8 test papers (PROTOCOL-P1 amendment
4), 1 plant each, built only if calibration passes.

**Target proof and prompt:** as X1. The case names the claim whose proof holds the plant, and the
prompt is X1's neutral "write a companion document explaining this proof" prompt, with no mention of
errors.

## Hit rule (judge)

Sonnet judge, no tools, double-judged with a tie-break, using X1's prompt with this definition:

- **FLAGGED**: the document says **at or next to the slipped step** that the paper's printed form
  is wrong or differs from what the document writes. A blanket note that does not point to this
  step ("minor typos have been corrected") is **not** a hit, because the reader still cannot find
  the error.
- **CORRECTED_SILENTLY**: the document writes the correct value without a located statement.
- **EXPLAINED**: the document reproduces the slipped form as valid.
- **OMITTED**: the step does not appear.

Hit = FLAGGED. The three misses are reported separately.

## Calibration (bare agent only)

8 dev cases × 2 bare runs = 16 runs. Keep bar: bare hit rate ≤ 0.70 (at least 5 of 16 runs not
FLAGGED). Above it, X2 stops before test. There is no tightening round, because the absorbed rule is
already the tightened form. The bare silent-correction rate is reported in either case: it is
a result in its own right.

## Test (only if calibration passes)

Arms `skill` (published, frozen at the commit recorded when test cases are built), `reduced` (a
single-pass SKILL.md, written after calibration, branch `explain-reduce`), and `without`. X1's tools
(no web, Agent allowed), timeouts and gate. 8 cases × 3 arms × 3 runs = 72 runs.

**Criteria (X1's):**
1. hit rate, skill − without ≥ +0.15;
2. FALSE other gaps per run, skill ≤ 1.5 × without (≤ 0.5 if without is 0);
3. reduced: hit rate ≥ skill − 0.10, FALSE gaps ≤ 1.5 × skill, cost ≤ 0.8 × skill.

The secondaries are as in X1 (other gaps REAL/FALSE against the original, fidelity, agreement,
cost and build). Reading table as in X1.

## Cost

Calibration 16 runs × ~$1.05 = ~$17. Test ~$190 (72 runs). Judge calls under $10.
