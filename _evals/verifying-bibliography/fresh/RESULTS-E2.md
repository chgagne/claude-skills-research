# Protocol E2 results: the given-name change recovers its error, no false positive (2026-10-26)

Protocol: `PROTOCOL-E2.md` (ae67eff). Arm reduced2 = `verifying-bibliography` at 5ee826d, E's six
bibliographies, 2 runs each, 21:42 to 22:24. No run failed or timed out; none discarded once the
scorer's mask covered the arm's own install path (`run/reduced2/`; E's regex only listed `full`,
`reduced` and `_shared`, the lesson already recorded for protocol D). Scorer
`private/score_e2.py`. Every entry the runs flagged had already been adjudicated in E, so E's pool
(18 confirmed errors) and verdicts apply unchanged.

| | E reduced (61ee681) | E full (bf62212) | E bare | **E2 reduced2 (5ee826d)** |
|---|---|---|---|---|
| Natural recall | 30/36 = 0.833 | 32/36 = 0.889 | 31/36 = 0.861 | **34/36 = 0.944** |
| False-positive entries | 8 | 7 | 12 | **3** |
| Trewartha (`phiala_detmold`) | 0/2 | 1/2 | 0/2 | **2/2** |
| Cost per run | $1.06 | $0.98 | $1.98 | $0.99 |
| Script ran | 12/12 | 12/12 | - | 12/12 |
| Web searches per run | 1.7 | 1.4 | 8.6 | 1.2 |

**Against the reading:** change holds. Trewartha flagged in both runs (the script printed it as
`MAJOR`), recall 0.944 (bar 0.783), 3 false-positive entries (bar 12), no `author-given-name`
false positive in any report.

The script printed `author-given-name` for three entries in all: Trewartha (real, flagged 2/2);
Bose, "Joey" for "Avishek Joey" (a middle name used as first name, dismissed by every run, as the
SKILL.md line says to); Kuciński, "Łukasz" against DBLP's "Lukasz" (a script defect: NFKD does not
decompose Ł, so the initials differed; dismissed by every run). The last one is fixed after E2 in
`_shared/scholarly/textnorm.fold` (Ł, Ø, Đ, Ð, Æ, Œ, Þ, ı mapped explicitly; new test
`test_letters_without_decomposition_fold_to_ascii`); that fix is unmeasured but removes a line
the agents already ignored.

**Limits.** Two runs per case and a pool made of earlier finds: the jump from 30 to 34 is four
hits, two of them Trewartha and a net two elsewhere (run-to-run variation in what the agents follow
up). It says the change did not cost anything here; it does not say the reduced skill now beats the
full one.
