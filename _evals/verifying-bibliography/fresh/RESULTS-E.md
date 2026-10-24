# Protocol E results: criterion missed by one hit; reduction kept (2026-10-24)

Protocol: `PROTOCOL-E.md` (b473f90), scorer committed by hash before any arm was read
(journal 2026-10-23). 36 runs on six fresh bibliographies, 2026-10-23 16:34 to 2026-10-24 08:11
(a reboot at 07:48 interrupted the launcher at 28 of 36; all 28 traces had been copied out, the
launcher resumed the rest). No run failed, none timed out, none was discarded.
Scores and every verdict: `results/E-2026-10-24.json`.

## Adjudication

29 entries were flagged by at least one run. Adjudicated once, arm-blind, by D's rules: 7 preprint
flags confirmed mechanically (DBLP or Crossref holds a peer-reviewed record), the other 22 by hand
against Crossref, DBLP, arXiv and the publisher. **18 confirmed errors** (9 preprint cited for a
published paper, 4 metadata, 4 authors, 1 nonexistent), 11 false positives.

The strict rule decided four borderline entries as false positives: two arXiv papers whose title
or author list changed in a later version while DBLP still shows the cited one, and two papers
whose arXiv comment says "accepted at ICML 2026" with no DBLP or Crossref record yet.

## Criterion

| # | Criterion | Reduced (61ee681) | Bar | Full (bf62212) | Without |
|---|---|---|---|---|---|
| 1 | Natural recall | 30/36 = 0.833 | at least 0.839 | 32/36 = 0.889 | 31/36 = 0.861 |
| 2 | False-positive entries | 8 (0.012) | at most 0.015 | 7 (0.010) | 12 (0.018) |
| 3 | Mean cost per run | $1.06 | at most $1.27 | $0.98 | $1.98 |
| 4 | Script ran | 12 of 12 | at least 11 | 12 of 12 | - |

**Verdict: criterion 1 missed by one hit (0.833 against a bar of 0.839); 2 to 4 met.** Against the
bare agent: full +0.03, reduced -0.03, i.e. one hit either way. Web searches per run: reduced 1.7,
full 1.4, bare 8.6. The skill's lasting gain on this material is cost (half the bare agent's), not
recall.

Sensitivity (not the criterion): counting the four borderline entries as errors, reduced 34/44 =
0.773, full 35/44 = 0.795, bare 35/44 = 0.795; the bar would be met.

## Where the reduced arm lost

Per error, hits out of 2 runs (full / without / reduced):

- `phiala_detmold`, "Trewartha, Amalie" for Daniel Trewartha (1 / 0 / 0). The script printed it in
  both reduced runs, as a `MINOR` `author-name-form`; both runs read it as a name-form difference
  and dismissed it. The full skill's text says nothing more about this finding; its one hit came
  from a run that checked Crossref by hand.
- `grathwohl2018scalable`, FFJORD title reordered and Sutskever missing (1 / 1 / 0). Found only by
  following up a title-search (`WEAK`) entry, which both skill texts ask for.
- `angermueller2019dynappo`, year 2019 for ICLR 2020 (2 / 2 / 1). The missing run wrote "DBLP
  lists it as ICLR 2020" in its notes and did not flag it.
- Gained: `bu2023optimal`, year 2023 for ICLR 2022 (1 / 2 / 2).

None of the misses traces to text the reduction removed.

## Decision (researcher, 2026-10-24)

The reduced skill stays published, with this result reported as a missed criterion. The
`author-name-form` finding is renamed `author-given-name` and raised to `MAJOR` from any record
(`compare.py`, `report.py`, SKILL.md, one new test); that change came after E and is **not
measured**.

## Limits

The pool holds only errors some run flagged, 18 of them, so one hit moves recall by 0.028 and the
0.05 bar sits within two hits. Two runs per arm cannot separate the skill versions on this
material.
