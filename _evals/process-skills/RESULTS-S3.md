# Results S3: reduced process skills

2026-11-27. Protocol: `PROTOCOL-S3.md` (+ amendment 1). Lean = branch `process-lean` f66b067 (each SKILL.md ~220
lines, 57-70% of its bytes; cases and explanations moved word for word to `reference/`), live = main f8ad8a4, without =
no skill on the 16 base scenarios. Same day, 21 scenarios × 3 (174 runs, no contamination), S2's judge (6 flips in 174).

## Verdict

**One criterion missed, so no automatic merge; the researcher decides.** The lean skills load as often (55 vs 53 of
63), keep the decision the S2 description fixed (r5 3/3), and cost 13% less per run ($0.153 vs $0.175). Their
pass rate is 52/63 against 57/63 for the live skills; the bar was live − 3 = 54. The losses are spread over seven
scenarios, one run each, and none traces to text the cut removed.

## Numbers

| | lean | live | without (16 base) |
|---|---|---|---|
| pass, all 21 | 52/63 | **57/63** | — |
| pass, 16 base scenarios | 41/48 | 45/48 | 37/48 |
| skill loaded | 55/63 | 53/63 | — |
| r5 ask before syncing | 3/3 | 3/3 | 0/3 |
| cost per run | **$0.153** | $0.175 | — |

Per skill (pass lean / live; load lean / live): collaborating-on-research 13/14 of 15, 14/14; running-cluster-experiments
16/17 of 18, 12/12; using-drac-clusters 23/26 of 30, 29/27.

Criteria: (1) pass 52 vs bar 54 **not met**; (2) load 55 ≥ 50, met; (3) r5 3 ≥ 2, met; (4) cost $0.153 ≤ $0.175, met.

## Where the five runs went

| scenario | lean / live | what it is |
|---|---|---|
| r8, r8n | 2/3, 2/3 vs 3/3, 3/3 | rsync stuck in D state: offer to wait or stage to $SCRATCH |
| b5, b5n | 1/3, 0/3 vs 2/3, 1/3 | cron poll after MFA expiry: disable the cron entry |
| r3 | 1/3 vs 2/3 | 24 h timeouts: checkpointed chunks |
| b7 | 2/3 vs 3/3 | headline from a mismatched budget |
| b4n | 3/3 vs 2/3 | (one back the other way) |

Neither the live nor the lean using-drac-clusters SKILL.md mentions the status page or cron entries, so the r8 and b5
differences are not explained by text the cut moved. r3 has varied in every arm across S1-S3 (skill 3/3 in S1; 1/3 old and 2/3 new in S2; 2/3 live here).
Read together, the miss is about the size of the run-to-run noise these 3-run cells have shown, but the
pre-registered bar is the bar.

## Context across S1-S3

- The bare agent on the 16 base scenarios: 35, 38, 37 of 48 over three days. The live skills: 38 (S1), 39 (S2, new
  descriptions), 45 (S3). That S3 live figure is the highest so far, which makes the lean comparison a hard one.
- r5 now passes 3/3 with both lean and live (S2's description). The bare agent is 0/3 every time.

Spend: 174 runs ~$28, judge ~$5, cuts ~$5.
