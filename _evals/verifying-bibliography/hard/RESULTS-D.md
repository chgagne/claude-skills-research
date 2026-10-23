# Protocol D results: long and identifier-poor bibliographies (2026-10-23)

Protocol: `PROTOCOL-D.md` with amendment 1 and the addendum, all pushed before the first scored
run (d9d0a7c). 36 runs (12 per arm), `claude-opus-5-5`, about $45 in model cost, one case at a
time behind the usage gate (5-hour window at most 45%, 7-day window 7% to 12%). The runs were meant
to start on 2026-10-21; the waiting script died in a reboot on 10-19, so they ran from 10-22 21:10
to 10-23 03:13. Scores, contamination record and the full adjudication: `results/D-2026-10-23.json`.

## Planted defects (the criterion)

13 page-range shifts in 364 entries (6 bibliographies, poor3 with none).

| Arm | Runs scored | Recall (13 x runs) | False positives after adjudication | Script ran |
|---|---|---|---|---|
| without | 12 | 1.00 | 15 of 562 (0.027) | - |
| skill (bf62212) | 12 | 1.00 | 15 of 562 (0.027) | 12 of 12 |
| self (frozen) | 11 | 0.52 | 13 of 298 (0.044) | - |

Denominators are clean entries (not planted, not a confirmed natural error) summed over scored
runs; before adjudication the raw counts were 123, 136 and 63 flagged entries.

The self arm's recall is 0.52 only because 5 of its 12 runs hit the 40-minute timeout and returned
no answer (scored as no flags, as the protocol's limits imply). Its 6 completed runs caught all 12
planted defects they contained. One self run (poor2, run 1) was discarded: it fetched the source paper from arXiv four times and
asked for its reference list verbatim.

**Verdict under the protocol: not a success.** The criterion needed the skill 20 points above both
arms on planted recall; skill and without are both at 1.00. Under "Reading the outcome", the
without arm is at ceiling, so the skill is worth only its script's systematic pass: it should be
reduced to "run the script, read the report" and the rest removed.

## Natural errors (secondary)

The six source bibliographies carry their own errors. 90 non-planted entries were flagged by at
least one run; each was adjudicated once from a sheet that listed the entry, the labels given and
no arm. 70 are real errors (63 arXiv preprints of published papers, 7 wrong author lists, all 7 in
benchmark technical reports: CEC 2005, 2013, 2017, 2019, 2020, 2022 and BBOB 2009). 20 are false
positives.

| Arm | Natural recall (runs x errors in case) | preprint | authors |
|---|---|---|---|
| without | 108/140 = 0.77 | 99/126 | 9/14 |
| skill | 121/140 = 0.86 | 110/126 | 11/14 |
| self (6 completed runs) | 50/53 = 0.94 | 43/46 | 7/7 |

Paired by entry and run, skill only 18, without only 5 (sign test p = 0.01, but entry-runs are not
independent). The pool holds only errors some run flagged, so these recalls are relative to the
union of finds, not to every error present.

## Cost

| Arm | Mean cost per run | Per entry | Median wall clock |
|---|---|---|---|
| without | $0.98 | $0.016 | 1.6 min |
| skill | $1.05 | $0.017 | 6.7 min |
| self | $1.72 | $0.028 | 36 min |

Timed-out self runs report a truncated cost (about $0.47 each), so the self figures are low.

## Reading

- The memory filter did its job on the planted defects, but the bare agent still reached every one
  of them: it wrote its own Crossref and DBLP lookups in Bash (curl loops) and compared page ranges.
  Page shifts on entries without a DOI are not hard for an agent with network access.
- Where the skill differs is coverage of the long tail it was not asked to plant: its scripted pass
  over every entry found about 9 points more of the natural errors at the same false-positive count
  and about the same cost. That is the "systematic pass" the outcome table already credits, so it
  points the same way: keep the script, cut the prose around it.
- The self-written skill is thorough but slow: 5 of 12 runs never finished in 40 minutes.

## Deviations and judgement calls

- `score.py` discards any trace that mentions `_evals`. Here the frozen skills were installed from
  `hard/private/run/`, so every skill and self trace matched on its own install path. Those three
  install prefixes were masked before scoring (`private/scored/prep.py`); no other `_evals` or
  `gold.json` mention remained. The same script applies the protocol's source-paper rule, which
  `score.py` does not implement: a tool call naming the source's arXiv id. Search results that
  merely list the source (7 traces, all arms) do not count.
- Preprint flags were settled by a rule when possible: confirmed when the entry cites only arXiv or
  CoRR and DBLP or Crossref holds a peer-reviewed record with the same title (55 of 69; 12 sampled
  by hand, all correct). The other 35 entries were checked by hand against DBLP, Crossref, the
  proceedings pages and the competition organisers' pages. An error not confirmed by such a record
  counts as a false positive (Mamba's COLM 2024 version, found only on secondary sites, and two
  "nonexistent" CEC large-scale reports that could not be shown not to exist).
- Four CVPR and ICCV entries give the CVF open-access page numbers, which differ from IEEE Xplore's
  (the numbers DBLP and Crossref carry). They were ruled correct.
- Some published versions (ICML and ICLR 2026) appeared after the citing paper was posted. They
  still count: the prompt asks whether a peer-reviewed version has been published.
- The adjudicator was Claude, the model family under test, working from the arm-blind sheet.
