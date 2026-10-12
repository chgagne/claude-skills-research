# Protocol B2 results: replication on 20 new drafts (2026-10-11)

Protocol: `PROTOCOL-B2.md`, pushed at 11e51b0 before any draft was built; skill frozen at
d6d64fa (the version protocol B measured). 80 runs (40 skill, 40 without), one case at a time
behind the usage gate, about $134 in model cost; no run lost to a limit, no format failure.
Scores: `results/B2-primary.json`, `results/B2-sensitivity-titlerule.json`. Gold labels:
`gold-B2.json`; the drafts stay private (arXiv source licences).

## Material

The eligible unused pool held 24 sources; 4 could not be built (too few removable references
or an unparseable bibliography) and were skipped, leaving exactly 20. In 7 of them fewer than 3
references were cited twice in the related-work section, so the selection code's fallback took
references cited there once (1 draft of 30 in protocol A). Memory probes: 55 of 120 removed
references named from memory; **25 non-memory key references** (floor 15), 40 non-memory random.
One draft (a new elementary-function operator) cannot really be disguised, since its formula
names it; it was kept and no run fetched it.

## Primary analysis (id rule; no run discarded)

| Arm | Runs | Recall@30 key non-memory (primary) | @10 | key memory @30 | random non-memory @30 | all @30 | all @10 | Already cited | Cost/run | Time/run |
|---|---|---|---|---|---|---|---|---|---|---|
| without | 40 | 0.200 | 0.180 | 0.829 | 0.087 | 0.421 | 0.317 | 0.3% | $0.94 | 94 s |
| skill (search method) | 40 | **0.260** | 0.220 | 0.886 | 0.163 | 0.454 | 0.292 | 0.4% | $2.42 | 139 s |

Skill minus without: **+6.0 points** (criterion 1, +15: not met). Already-cited share 0.4%
against 0.3% (criterion 2: not met, by one candidate's worth). Exact McNemar on 240 (reference,
run) pairs: 3 only-skill, 0 only-without, p = 0.25. **Verdict under the protocol: not met.**

## Sensitivities

- No run discarded: identical to the primary (the id rule discarded nothing).
- Protocol B's rule (id or 60% of title words): 4 runs discarded (2 skill, 2 without);
  skill 0.255 vs without 0.208, +4.7 points.

## Secondary: B and B2 pooled under the id rule

The id rule discards no protocol-B run either, so B under it is B's no-discard figure (+11.7).
Pooled over 45 non-memory key references: skill 44/110 = **0.400**, without 34/110 = **0.309**,
**+9.1 points**; McNemar 11 vs 1, p = 0.006. Declared secondary before the runs because B's
no-discard result was already known; it decides nothing, but it is the best single estimate.

## Reading

- The search method's advantage on hard references replicated in direction, not in size:
  +6 on new drafts against +12 to +18 on B's drafts. Across both sets the skill almost never
  misses a reference the bare agent finds (1 pair in 12 discordant ones).
- The new drafts are harder for both arms (without: 0.20 here, 0.34-0.40 in B), partly because
  7 of 20 relied on the fallback key rule, so "key" is a weaker label here.
- The skill also does better on non-memory random references (0.163 vs 0.087) and on overall
  Recall@30 (0.454 vs 0.421), unlike B where overall recall was flat; it gives up some
  Recall@10 (0.292 vs 0.317).
- It costs 2.6 times as much per run.
- B's title-word rule was not what produced its gain: under the id rule neither protocol
  discards anything, and the B2 estimate is lower without any discard at all.

Per the protocol's outcome table: criterion not met, skill above without. The skill stays as is;
its "Measured result" paragraph now gives the B2 figure as the estimate.
