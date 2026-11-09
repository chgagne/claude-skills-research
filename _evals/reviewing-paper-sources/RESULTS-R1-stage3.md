# Results R1 stage 3: documented internal defects (arXiv v1 fixed in v2)

2026-11-09. Protocol: `PROTOCOL-R1-stage3.md` (+ amendments 1-2). Material in
`private/r1s3/` (gitignored). Probe: direction only, no pass bar.

## Verdict

**No difference between the arms. Both find about 80% of real, author-confirmed internal
inconsistencies, and both miss the same ones.** Reviewing post-cutoff arXiv v1 papers, the skill
found 19 of 24 documented defect-runs and the bare agent 20 of 24. They are identical on 7 of 8
papers, and the one difference is a single run. The skill costs 1.57 times as much.

## Numbers

8 papers, 12 defects the authors fixed in a later version, 2 runs per arm (claude-opus-5-5, no
web, R3's review prompt; skill frozen at d2329ee with R3's fixed form):

| arm | defect-runs found | papers with ≥1 found | same verdict in both runs | issues per run | cost per run |
|---|---|---|---|---|---|
| skill | 19/24 (0.79) | 7/8 | 11/12 | 28.5 | $1.68 |
| without | 20/24 (0.83) | 7/8 | 12/12 | 28.1 | $1.07 |

Per-paper skill-minus-without: 0 on seven papers and −1 on one (2608.15428, defect #0, found in one
skill run of two). Total −1, so the protocol's rule reads "no difference visible at this size".
Judge: Sonnet, run twice, 0 flips in 48. Every one of the 39 FOUND quotes was read against its
review. All are explicit, with the correct value or the contradicting location ("2·0.79/1.79 =
0.883, not 0.83"; "the 'variants' column sums to 57, which is … combinations, not the 21
variants"). The misses were checked by searching every review for the defect's key terms: none of
them mentions the missed defect, so the judge did not under-count.

## What both arms found and what both missed

Found in all 8 of 8 runs: a wrong F1 from the paper's own class split, a reversed direction stated
twice, "over thirteen" vs "twelve" scene factors, a table column labelled "variants" summing to
57 against "21 variants", "0.0% for all Claude models" against a 4.17 cell, a taxonomy figure
disagreeing with the method table in 11 entries, and two of the four count/range slips in
2608.15428.

Missed in all 8 runs: "seven depths" followed by six listed values (2609.10739), and "all eleven"
models against the paper's thirteen (2608.15428, #3). Both are bare counts with no arithmetic
attached: a number word that disagrees with a list or a total stated elsewhere.

## Reading

Real documented defects behave like the planted ones in R1 stages 1-2: the bare agent already
cross-checks numbers and claims against tables, and the skill adds nothing measurable to that
ability. The skill's measured contribution so far remains the review's form and coverage (R2,
R3), at higher cost. Stage 3 closes the R1 thread.

The two shared misses point to one gap: **a count word that disagrees with an enumerated list or a
total stated elsewhere.** Per the C2 lesson, prose guidance would probably not be executed, but a
check whose output the agent must answer could be (for example, a script that lists every
"N <noun>" claim with the enumerations and totals that could contradict it). That would be a new
design, measurable on this material plus the reserve paper (2607.24016, 6 defects). It is the
researcher's call.

## Notes

- 28 diffs read to find 8 eligible papers; 202-entry pool. Screening and rejections are in
  `private/r1s3/decisions.json`.
- The scorer was fixed three times before any verdict was read, each fix recorded in the journal:
  the frozen-skill path under `_evals` was masked; the title rule was dropped, because these runs have
  no web tools and one run grepped its own `pdftitle`; JSON parsing was made tolerant of raw LaTeX
  backslashes and tabs. One run's 4 judge prompts changed as a result; their earlier verdicts were
  set aside unread and the prompts re-judged.
