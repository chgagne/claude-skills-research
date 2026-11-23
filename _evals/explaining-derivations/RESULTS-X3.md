# Results X3: a reduced explaining-derivations SKILL.md

2026-11-22. Protocol: `PROTOCOL-X3.md` (+ amendment 1). Lean = branch `explain-lean` 9c7b663 (SKILL.md 316 → 180
lines), live = main 2d980c0, run the same day on X2's 8 absorbed-slip cases, 2 runs each (32 runs, no
contamination). Judged with X2's prompts (Sonnet, double-judged; 0 plant flips).

## Verdict

**Two criteria missed, both narrowly, so no automatic merge; the researcher decides.** The lean skill
flags every slip (16/16, same as live), builds every document (16/16), and raises as many real gaps. It
raises 3 more gaps judged FALSE over 16 runs (7 vs 4; bar 6), and costs $0.02 more per run ($1.23 vs
$1.21). Four of lean's 7 FALSE gaps are on one case (x2_d1_a), where both runs complained about a lemma's
uniformity in a way the judge, which never saw the lemma, ruled false.

## Numbers

| per run | lean (180 lines) | live (316 lines) |
|---|---|---|
| slip flagged at the step | **16/16** | 16/16 |
| other gaps judged REAL | 2.06 | 1.69 |
| other gaps judged FALSE | 0.44 (7) | 0.25 (4) |
| misstatements of the source | 0.06 | 0.00 |
| PDF built | 16/16 | 16/16 |
| cost | $1.23 | $1.21 |
| document length (chars) | 25,300 | 26,100 |
| `run-explain.py --plan-only` run / assembled | 16 / 0 | 13 / 0 |

Criteria: (1) 16 ≥ 14 met; (2) 0.44 vs bar 0.38 **not met**; (3) 16 ≥ 15 met; (4) $1.23 vs $1.21 **not met**.

## The FALSE labels are noisy

The judge sees the target proof and the document, not the whole paper. Checked against the sources:

- **x2_d1_b (3 FALSE: 1 lean, 2 live): judge error.** The documents say the paper defines
  W^{3,1}_0 with derivatives in L^3, so "φ ∈ W^{3,1}_0" does not follow from u ∈ L^1. The paper does
  print L^3 (l.2009). That is a genuine typo in the published paper, not our plant (the plant is a
  T^{-2} exponent). The judge said it "could not check the definition". With these 3 corrected, the count is
  lean 6, live 2, which is further from the bar.
- **x2_d1_a (lean 4, live 1): partly arguable.** The lemma as stated gives constants for one fixed G.
  Applied to a G that depends on u, uniformity in u is not delivered by the statement, so "the statement
  does not deliver that" is defensible. "C denotes both constants" is genuinely false (the original
  writes C′). Not re-adjudicated: the protocol scores the judge.

At 2-7 FALSE gaps per 16 runs, concentrated on one or two cases, criterion 2 cannot tell the arms apart
reliably either way.

## What the bench shows about the skill itself

This is the first time the skill was run on this material. **Neither arm ever used the pipeline.** Most
runs ran `--plan-only` and then wrote the companion by hand: no subagent dispatch, no fragments, no gap
ledger (`gaps.json` 0/32). The prompt asks for a document under `companion/`, and a one-claim job does not
pull the agent into the three-phase workflow. So X3 measured how the SKILL.md text shapes a hand-written
companion, not the machinery. Against X2's bare runs on the same cases (different day, context only), both
skill arms flag as often (16/16) and cost more ($1.2 vs $0.85).

Spend: 32 runs ~$39, 2 dev runs ~$2.5, judge ~$3.
