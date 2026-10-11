# Protocol C results: the long-tail bibliographies with the tools working (2026-10-10)

Protocol: `PROTOCOL-C.md`, pushed at 6ad2dac before the first scored run. 36 runs (12 per arm),
`claude-opus-5-5`, $9.7 in model cost, launched case by case behind the usage gate (the account
stayed at or under 14% of the 5-hour window and 40% of the 7-day window). No run error, no
contaminated trace. Scores: `results/C-2026-10-10.json`.

| Arm | Recall (17 defects x 12 runs) | False positives (41 x 12) | Label accuracy | Script ran |
|---|---|---|---|---|
| without | 1.00 | 0 | 1.00 | - |
| skill (bibcheck at ee2fbc2) | 1.00 | 0 | 1.00 | 12 of 12 runs |
| self (frozen bibverify.py) | 1.00 | 0 | 1.00 | 12 of 12 runs (dblp.org refused, by design) |

**Verdict under the protocol: not a success** (no recall gap). Every arm is at ceiling.

## Reading

- The scripts now run inside the eval sandbox, so the correction notices on the earlier long-tail
  and stage-1 results are resolved by measurement, not by argument: with its tools working the skill
  still adds nothing measurable on these cases.
- These defects are all reachable through a Crossref lookup or a web search, which the bare agent
  does by itself (protocol C's without arm reached 1.00 here against 0.98 in the first long-tail
  run). The cases no longer discriminate between arms, for any agent with web tools.
- What would: bibliographies whose errors need a source the agent does not reach by default (no
  DOI and no web-visible record, e.g. old proceedings, theses, non-English venues), or the cost of
  checking a long bibliography (60-150 entries), where a script's systematic pass may beat an agent
  sampling entries. Neither is measured yet.
