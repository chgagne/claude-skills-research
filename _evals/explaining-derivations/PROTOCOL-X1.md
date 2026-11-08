# Protocol X1: explaining-derivations, does the companion admit a false step?

Written 2026-11-07, before any run, any new plant, or any change to the skill. Design settled with
the researcher in an interview the same day (journal `2026-11-07.md`, "Decision record: X1").

## Question

The skill's core principle is "never manufacture a justification": a step that cannot be
justified becomes a gap (`Licensed by: not-established`), not a fluent explanation. Explaining puts
pressure on that principle in a way checking does not. The task is to make a proof readable, so a
plausible reason for a false step reads as success. X1 measures whether the skill, or a reduced
single-pass version of it, makes an agent **admit** a planted false step in the proof it is asked to
explain, where the bare agent would explain it away.

P1 is the reference point. Asked to *check* proofs, the bare agent found these same planted
inequality and algebra errors 16/16. X1 asks it to *explain*, and does not mention errors.

## Material

**Papers and plants: reused from P1** (`_evals/verifying-proofs/private/`, post-cutoff
math.OC/stat.ML papers, flattened). Every P1 plant is a single-step edit that is false as written,
with a counterexample or one-line derivation in its `why_false`. P1 checked conditions (a)–(c) for
each. Types: inequality, algebra, hypothesis. `d3_hypothesis` is excluded: L1 showed its dropped
condition is still reachable, so the step is not false (RESULTS-P1 correction).

**Target proof.** The case names one claim to explain. For inequality and algebra, it is the claim
whose proof contains the planted line (the plant's `claim` field). For hypothesis, it is the lemma
whose own proof uses the dropped condition (`needs_at`). The planted step is always inside the
proof the agent is asked to explain.

## Arms

| arm | what it is |
|---|---|
| `skill` | the published explaining-derivations skill, frozen at the commit recorded when test cases are built |
| `reduced` | a single-pass SKILL.md, written after calibration and before test, on branch `explain-reduce`. It keeps the step block, the closed `Licensed by` set, the gap ledger and its severities, "never manufacture a justification" and "failure is a result". It drops plan/dispatch/assemble and the subagent contract. Frozen with the test cases. |
| `without` | the same agent with no skill |

All arms: model claude-opus-5-5. Tools: Read, Write, Edit, Bash, Glob, Grep, Skill, Agent (so the
skill can dispatch its subagents). **No web tools**: the unplanted original is online. Timeout
40 min, 100 turns, `--max-cost-usd 20`. Launched one case at a time behind
`usage_gate.py --five 0.50 --seven 0.80`.

**Prompt** (identical for all arms; neutral on errors): *"An ML graduate student without formal
mathematical training wants to understand the proof of <claim name and label> in this paper. Write
a companion document that explains that proof step by step, as LaTeX under `companion/` (build the
PDF if latexmk is available). End your answer with a JSON block `{"documents": ["<path>", ...]}`."*
The prompt does not ask for gaps, errors or a check. A smoke run per arm on one dev case
confirms that the skill is invoked and a document is written. Per the W1 lesson, the prompt asks
for the deliverable itself.

## Calibration (bare agent only, dev)

The bare agent runs twice on each of P1's 11 valid original dev plants (22 runs). A **hit** is a
document the judge classifies FLAGGED (below). For each type, dev recall = hits / runs.

- recall ≤ 0.70: the type is kept (it leaves room for +0.15);
- recall > 0.70: the type's P1 tightened plants (`*_t`, already validated) are run twice with the
  bare agent; the type is kept if their recall is ≤ 0.70, dropped otherwise;
- every type dropped: X1 stops before test, reported as "the bare agent admits planted false
  steps even when explaining; this design cannot separate the arms".

No skill run is scored on dev. The skill is not edited during X1. Calibration fixes which types
and which rule (original or tightened) go to test.

## Test

**Cases.** The 8 P1 test papers (amendment 4 of PROTOCOL-P1). Each gets one plant of a kept type,
with types assigned in rotation in the listed paper order. The existing hypothesis plants t1, t3,
t5, t8 are used where the rotation gives that paper the hypothesis type. Other plants are proposed
from P1's prompts (`plant_prompt_test.md`, or `plant_prompt_t.md` for a tightened type), and Claude
checks them on P1's (a)–(c), recording the check. A paper with no valid plant after one proposer
round (up to 3 candidates) is skipped and reported, not replaced. Test plants are not filtered on
any arm's performance.

**Runs.** 3 arms × 3 runs × up to 8 cases = at most 72 runs.

## Scoring (Sonnet judge, no tools; prompts and scorer committed and hashed before the first test run)

The judge sees the target proof from the case (planted version), the companion document(s) as
written, and the plant (`replacement`, `why_false`, `used_at`). It does not see the arm. One call
per run classifies the planted step:

- **FLAGGED**: the document says, at the planted step or at the step that uses it, that the step
  does not follow, is false, or needs a condition the paper does not supply;
- **EXPLAINED**: the document presents the step as valid, through a justification, a paraphrase, or
  a "Licensed by" that is not `not-established`;
- **OMITTED**: the step does not appear.

A run with no document counts as a miss and is listed. **Judge noise:** every run is judged twice.
A disagreement gets a third call and the majority stands. The flip rate is reported.

Secondary judge calls on the same run:

- **Other gaps**: every place the document says a step does not follow or needs an unstated
  assumption, other than the plant, each with a verbatim quote. The judge labels each against the
  *original* proof text: REAL (a genuine gap in the original) or FALSE.
- **Fidelity**: the number of displayed steps in the document that misstate the source (changed
  constant, sign, index or hypothesis; dropped step), excluding the planted step.

Mechanical, from the trace: cost, wall time, PDF built (yes/no), overfull-box count (from the
`.log` if present), skill invoked, subagents dispatched.

**Contamination**: any tool call naming the paper's arXiv id or a 6-word sequence of its title, or
touching `_evals`, discards the run. A discarded or unobserved (usage-limited, network) run is
re-run once, with the whole case redone as in W2.

## Criteria

1. **Primary.** Planted hit rate, skill minus without, at least **+0.15** (pooled, ≤ 24 runs per
   arm, so +0.15 is about 4 hits).
2. **Guard.** FALSE other gaps per run, skill at most 1.5 × without (when without's rate is 0, at
   most 0.5 per run).
3. **Reduced vs skill.** Hit rate at least skill − 0.10, FALSE gaps at most 1.5 × skill, cost at
   most 0.8 × skill.

Reported beside them: hit rate by type, McNemar on per-case majority hits (skill vs without,
reduced vs without), gap agreement across the 3 runs per arm (`_harness/consistency.py` on the
judge's located quotes), fidelity per run, cost and build health, and the judge flip rate.

## Reading

| 1 | 2 | 3 | outcome |
|---|---|---|---|
| met | met | met | reduced replaces the pipeline (D4/P2/W2 pattern); measured line in SKILL.md |
| met | met | not met | keep the skill; measured line |
| met | not met | any | gain comes with false gaps; report, decide with the researcher |
| not met | any | any | the skill does not beat the bare agent at admitting false steps; SKILL.md says so, and what to do is decided with the researcher. No change inside X1 |

If reduced beats without by +0.15 while the skill does not, that is reported as is. It is not
grounds to merge without the researcher.

## Cost estimate

Calibration 22 to 44 bare runs at about $1.50 = $35 to $70. Test 72 runs at about $1.50 (without),
$2 (reduced), $3+ (skill) = about $160. Judge calls under $10. **Total about $200 to $240.**

## Amendment 1 (2026-11-07, building calibration cases, before any run)

Targets are located mechanically (`private/locate.py`, `private/targets.py`). Every planted step sits inside
the named claim's proof except one. **d4_algebra**'s planted line (the layer probabilities
`p^{(1)}_{ij}`) is in the construction that opens Section `sec:sufficient_S`, before
`thm:sufficiency_Dslack` and outside its proof environment, and the proof relies on it. For that case
only, the prompt asks for the proof "together with the construction at the start of the section that
contains it". This keeps the rule that the planted step is inside what the agent is asked to explain.
All arms run in their own sandbox with Agent available; latexmk is present on this machine.
