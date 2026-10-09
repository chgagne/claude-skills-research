# Long-tail results (2026-10-09)

> **Correction, 2026-10-09 (found while setting up the surveying-literature eval).**
> Neither tool-using arm ran its script. Inside `claude plugin eval`, each run gets a
> fresh HOME without `~/.claude/skills/_shared`, so `run-bibcheck.py` crashed on import in
> every call that reached it (18 of 24 calls; the other 6 only listed or read files); and the run's sandbox denies all outbound
> network to Bash, so the self-written skill's `bibverify.py` got "deny network-outbound
> api.crossref.org:443" in 18 of its 19 calls. All three arms therefore ran as
> the agent plus WebFetch/WebSearch, steered by different instructions. What follows
> measures the skills' *instructions*, not their tools. The skill arm's 244 Crossref calls were WebFetch calls made by the agent, not by bibcheck. A rerun with the shared
> module installed and Bash network allowed is needed before any claim about bibcheck itself.

Protocol and frozen cases: `PROTOCOL.md`, commit 5428132, pushed before the first run.
54 runs, `claude-opus-5-5`, no format failure, no contaminated trace, no run error.
Scores: `results/longtail-2026-10-09.json`. Labels: `gold.json`, published with this file.

| Arm | Recall (17 defects x 18 runs) | False positives (41 x 18) | Label accuracy | Cost per run | Time per run | Crossref calls |
|---|---|---|---|---|---|---|
| without | 0.980 (1 miss) | 1 | 1.00 | $0.54 | 52 s | 213 |
| skill | 1.000 (0 miss) | 0 | 1.00 | $0.65 | 81 s | 244 |
| self | 0.941 (3 misses) | 1 | 1.00 | $0.66 | 375 s | 186 |

Misses: without missed the ViSymRe preprint once; self missed three lt2 defects in one run.
False positives: one correct entry in each of without and self.

## Verdict under the protocol

- Criterion 1 fails: the skill's recall gap is 2 points over without and 6 over self, not 20.
- Criterion 2 holds: the skill has no false positive, the other arms one each.
- Indicative McNemar, skill vs without on (defect, run) pairs: 1 discordant pair in the
  skill's favour, 0 against, exact p = 1.0.

The pre-registered reading is **not a success**.

## The stopping rule misfired

The protocol says: if the without arm still exceeds 0.8 recall, the memory filter failed and
the result is uninformative. The without arm reached 0.98, so the rule as written applies.
But the condition it was meant to detect did not happen. The no-tool confirmation probe on
these same cases caught 1 of 18 defects, and the without arm's traces show real
verification: 213 Crossref calls, 15.8 turns per run against 2.8 at stage 1. The rule took
"high recall without the skill" as a proxy for "memory leak", and that proxy was wrong: a
model with web tools and no skill verifies references. The rule is reported as written
and as wrong, and the substantive reading below rests on the traces, not on it.

## What the result shows

With Bash and WebFetch, Opus 5.5 checks long-tail and post-cutoff references against
Crossref by itself, nearly as well as with the skill. The skill's measurable contribution
here is consistency: 18 of 18 runs perfect, against one miss and one false positive for
the bare agent. That costs about 20% more per run and 55% more time. The self-written
skill did worse than no skill and took seven times as long.

Two limits: 17 defects x 18 runs cannot separate 98% from 100%, and every defect here is
checkable through Crossref. The skill's own design claims more for entries with no DOI
(DBLP and title-search rungs), and DBLP served scripts an anti-bot page throughout.
