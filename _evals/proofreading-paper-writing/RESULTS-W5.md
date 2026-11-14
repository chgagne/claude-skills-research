# Results W5: a fresh-eyes second pass, one subagent per section

Protocol: `PROTOCOL-W5.md` (2146387; amendment 1 89b6ae0, frozen material hash 021b2287). 54 runs,
2026-11-12 22:19 to 2026-11-13 12:18 at the standing 0.50/0.80 gate, none failed, every final message
carried a parsable JSON block. All arms judged in one session (2026-11-13). Scoring:
`private/w5/score_w5.py score` (sha256 prefix 885e20ccbfe4).

## Verdict

**Both criteria met.** With a second pass by one fresh subagent per section, the skill covers 0.639 of the
judged-real writing defects against 0.567 for the bare agent (bar: at least bare - 0.05) and 0.453 for the
published skill, with the lowest judged-harm share of the three arms (0.085 vs 0.141 bare). It costs 2.3x the
bare agent per run ($5.42 vs $2.31).

## Arms

| arm | what it is |
|---|---|
| pass2 | the published skill (open criterion) + step 2b: `second-pass.py split`, one subagent per section with `reference/second-pass-prompt.md`, `second-pass.py merge` (refuses until every section answers); branch `proofread-pass2` 5a11ad7 |
| current | the published skill (open criterion, 78e4580) |
| without | same agent, same prompt and tools, no skill |

## Results, 6 new fresh post-cutoff drafts x 3 runs per arm

| measure | pass2 | current | without | criterion |
|---|---|---|---|---|
| coverage of judged-REAL clusters (character overlap) | **0.639** | 0.453 | 0.567 | pass2 >= without - 0.05: **+0.072, met** (pass2 higher on 5/6 drafts) |
| judged harmful share, 15 sampled per run | **0.085** (23/270) | 0.107 (29/270) | 0.141 (38/270) | pass2 <= without: **met** |
| pass2 - current, coverage | +0.187 (6/6 drafts) | | | reported |
| coverage, line rule | 0.775 | 0.591 | 0.661 | reported |
| agreement across runs, line / character rule | 0.857 / 0.677 | 0.842 / 0.725 | 0.854 / 0.746 | reported |
| REAL clusters hit by this arm only | 84 | 12 | 57 | reported |
| proposals per run | 98.0 | 61.6 | 75.8 | |
| share of located proposals in a REAL cluster | 0.633 | 0.703 | 0.697 | |
| REAL hits per run | 62.0 | 43.3 | 52.8 | |
| per run: mechanics / style / flow / framing | 32.7 / 43.9 / 3.8 / 17.6 | 25.4 / 19.8 / 3.1 / 13.3 | 30.8 / 19.8 / 7.0 / 18.2 | |
| cost per run | **$5.42** | $2.19 | $2.31 | no bar |

Reference set (character rule): 526 of 988 clusters judged REAL.

## Compliance

The fan-out ran in **16 of 18** `pass2` runs (5 to 13 subagents, 25 to 103 rows merged). Two runs
(2608.06407 run 1, 2609.01788 run 0) never ran `split` and went from the first ledger straight to rendering;
nothing stops that, since only `merge` enforces the fan-out and the renderer does not check for it. Their
coverage (0.51, 0.55) is at the `current` level. They are scored as part of the arm, as the protocol says.

## Reading

- **A second reading by fresh context closes the gap and passes the bare agent.** The prose instruction to
  re-read was not executed (first dev gate); the same intent, made structural (a script that splits, a
  merge that refuses), was executed in 16/18 runs and added 25-103 rows each.
- **The extra rows are mostly real, and not harmful.** Per row the second pass is a little less precise
  (REAL share 0.63 vs 0.70), but it lands more real defects per run (62 vs 53 bare), and the precision judge
  finds the fewest harmful edits in this arm. Style rows double (44 vs 20 per run).
- **Stability is not better:** line-rule agreement 0.857 vs 0.854 bare; character-rule agreement is lower
  (0.677 vs 0.746), as expected when each run adds many rows the others do not.
- **The price is 2.3x the bare agent.** The skill was cheaper than bare before W5; it is now the most thorough
  and most expensive arm.
- Bare coverage on these drafts (0.567) is lower than on W3's and W4's (0.684, 0.653); `current` is stable
  (0.438, 0.435, 0.453). Coverage is relative to each protocol's pooled reference set, so cross-protocol
  values are not comparable in level, only within a protocol.

## Caveats

- Coverage is relative to the pooled reference set; the arm proposing most hits most of it by construction.
  REAL hits per run and the arm-only counts are reported beside it.
- No judge test-retest in W5 (W3: 0.80 on 80 clusters).
- 6 drafts; direction by draft only.

## Outcome

Outcome row "both met": merge `proofread-pass2` with a measured line. Held for the researcher's go-ahead,
because of the 2.3x cost and the 2/18 runs that skipped the fan-out (both are decisions about the
published skill, not about the measurement).
