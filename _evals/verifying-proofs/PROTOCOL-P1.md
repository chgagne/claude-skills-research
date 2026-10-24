# Protocol P1: verifying-proofs on planted proof errors

Written 2026-10-23, before any paper was downloaded or any error planted. Design settled with the
researcher in an interview the same evening (journal `2026-10-23.md`, "Decision record:
verifying-proofs P1").

## Question

Does the skill help an agent find an invalid step in a proof that it would miss on its own? The
skill says its default run is a hygiene checker and that correctness needs check scripts written by
the agent. This protocol measures what the whole skill (instructions + script) adds over the bare
agent on one task: find the broken step.

## Material

**Pool.** arXiv submissions from 2026-07-01 to 2026-10-15 (after the model's training cutoff)
whose primary category is math.OC or stat.ML (cs.LG was in the interview's wording; its listing
exceeds the API's 30,000-result cap and is mostly papers without proofs, so it was dropped before
anything was listed), listed by the arXiv API and screened in a shuffled order (seed 20261023). A paper is eligible when its LaTeX source has at least 5 `proof`
environments with 1,500 to 40,000 words of proof text in total, flattens to a single
`.tex` (inputs inlined, comments stripped), and has no author in the researcher's group. The first
12 eligible papers are used: 4 dev and 8 test, assigned in screening order (first 4 dev).

**Plants.** One plant per case, at a single step of one proof. The statement of every theorem and
lemma is left unchanged except for the dropped-hypothesis type, where the change is the plant.
Three types:

- **inequality**: one step of an inequality chain changes direction or loses a factor or constant,
  so the chain no longer gives the bound the following steps use;
- **hypothesis**: a lemma statement loses a condition its proof uses, and a later proof still
  applies the lemma where only the dropped condition makes it hold;
- **algebra**: a wrong exponent, a dropped term or a wrong constant in an expansion or
  simplification, and later steps use the wrong form.

A plant is valid only when (a) the changed step is false as written, shown by a concrete
counterexample or a one-line derivation recorded in the plant file, (b) the rest of the proof is
unchanged, so the broken step really is used, and (c) the edit changes at most 3 source lines.
A subagent proposes plants from a fixed prompt; Claude checks (a)-(c) for each one and records the
check. A rejected plant is replaced by the next proposal of the same type in the same paper. Plants
are stored in `private/plants/<case>.json` (original lines, new lines, justification, line span).

**Cases.** Dev: each of the 4 dev papers × each of the 3 types = 12 cases. Test: each of the
8 test papers × 2 plants of different types, types assigned in rotation over the types kept after
calibration, at least 3 proofs apart within a paper = 16 cases. Each case is a separate copy of the
paper with exactly one plant.

## Calibration (dev, bare agent only)

The bare agent runs twice on each of the 12 dev cases (24 runs). For each type, dev recall is
hits / 8.

- recall ≤ 0.50: the type is kept as is;
- recall > 0.50: the type's plant rule is made subtler once (written down before the re-run: the
  broken step must sit inside a chain of at least 3 displayed steps and the error must not change
  the final displayed bound's form), 4 new dev plants of that type are built, and the bare agent
  reruns them twice; kept if recall is now ≤ 0.50, dropped otherwise;
- every type dropped: P1 stops before test, and the result is reported as "the bare agent catches
  planted single-step errors in these papers; this design cannot separate the arms".

Calibration fixes the plant rules. Test plants are not filtered on any arm's performance.
No skill run happens on dev, and the skill is not edited during P1.

## Arms

| arm | what it is |
|---|---|
| `skill` | the published verifying-proofs skill, frozen at the commit recorded when test cases are built |
| `without` | the same agent with no skill |

Both arms: model claude-opus-5-5, tools Read, Write, Edit, Bash, Glob, Grep, Skill. **No web
tools in either arm**: the unplanted original is online and would be an answer key. Timeout 40 min,
100 turns, `--max-cost-usd 20` per call. 2 runs per case per arm, 64 test runs, launched one case at
a time behind `usage_gate.py --five 0.40 --seven 0.75`.

**Prompt** (identical for both arms): a co-author sent this paper, check its proofs for errors,
end with a JSON block `{"flagged": [{"quote": "<at least 20 characters copied verbatim from the
step>", "claim": "<theorem or lemma it belongs to>", "problem": "<what is wrong>"}]}` and an empty
list if nothing is wrong.

## Scoring

- **Hit**: a flag whose `quote`, after whitespace and `$` normalisation, matches the case's `.tex`
  at a location overlapping one of the case's hit spans, each widened by 3 lines on each side:
  the planted lines; the `used_at` step that relies on the broken form; and, for the hypothesis
  type, the `needs_at` step of the lemma's own proof that uses the dropped condition. A quote that
  matches nowhere does not count as a hit. Location only: the `problem` text is not graded.
  Matching is done by a script written and committed before any test run. (Amended 2026-10-23,
  before any plant was accepted: the first wording counted only the planted lines and the lemma
  statement, and would have missed a correct report placed at the step the error breaks.)
- **Other flags**: every flag that is not a hit. Counted per run. From the pooled other flags of
  both arms, 20 are drawn with seed 20261023 and adjudicated arm-blind by Claude as a real defect
  of the original paper, a defect caused by the plant elsewhere, or a false alarm.
- **Contamination**: any tool call naming the paper's arXiv id or a 6-word sequence of its title,
  or touching `_evals`, discards the run; a discarded or usage-limited run is re-run once.
- **Script ran**: a Bash call to `run-proofcheck.py` in a skill run.

## Criterion (both must hold)

1. Planted recall, skill minus bare, at least +0.15 (pooled over 32 runs per arm).
2. Other flags per run, skill at most 1.5 × bare.

Reported beside it: recall by plant type, McNemar on per-case majority hits, cost and wall time per
run, script runs, and the 20 adjudicated flags.

## Reading

- Both met: the skill helps on single-step errors; SKILL.md's measured section gets the number.
- 1 met, 2 not: the gain comes with noise; report both and decide with the researcher.
- 1 not met: the skill does not beat the bare agent on this task; SKILL.md says so, and what to
  change (or whether to reduce the skill, as for verifying-bibliography) is decided with the
  researcher. No change is made to the skill inside P1.

Cost estimate: dev 24 to 40 runs and test 64 runs, at about $1.50 to $4 per run, so $130 to $420.
