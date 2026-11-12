# Results W3: a category form the writing report must answer

Protocol: `PROTOCOL-W3.md` (7a59cbe; amendment 1 fdb0d2a, frozen material hash 1637b08e; amendment 2
4b13920/639a780, usage ceiling only). 72 runs, 2026-11-11 19:51 to 2026-11-12 04:48, none failed, every
final message carried a parsable JSON block, skill invoked in 54/54 skill runs, no subagent in any run.
Scoring: `private/w3/score_w3.py score --plant-verdicts plant_verdicts_w3.json` (scorer f5ff549af6d7).

## Verdict

**Neither primary met: the form changes nothing measurable, and both skill arms cover a third fewer real
defects than the bare agent.** The checklist is filled in every run and the agent's `none` cells name where
it looked, but `form` covers 0.45 of the judged-real defects against 0.44 for the published skill (bar
+0.10) and agrees with itself across runs 0.82 against 0.80 (bar +0.05). The bare agent covers 0.68, higher
on 6 of 6 drafts, because it proposes half again as many rows and the extra ones are real as often as the
skill's. No merge.

## Arms

| arm | what it is |
|---|---|
| form | proofreading-paper-writing at `proofread-form` 5bfea40: 14-category checklist in `writing-report.md`, `category` on every ledger row, `check-writing-form.py` |
| current | the published skill (W2 single-pass reduction) |
| without | same agent, same prompt and tools, no skill |

## Results, 6 fresh post-cutoff drafts x 3 runs per arm

| measure | form | current | without | criterion |
|---|---|---|---|---|
| coverage of judged-REAL clusters (character overlap) | **0.450** | 0.438 | 0.684 | form - current >= +0.10: **+0.013, not met** (4/6 drafts positive) |
| pairwise agreement across runs (W1 line rule) | **0.824** | 0.800 | 0.848 | form - current >= +0.05: **+0.024, not met** (4/6 drafts positive) |
| coverage, line rule (reported) | 0.612 | 0.595 | 0.797 | |
| agreement, character rule (reported) | 0.679 | 0.669 | 0.708 | |
| Jaccard of REAL clusters hit, run pairs | 0.607 | 0.608 | 0.678 | |
| proposals per run | 54.6 | 53.1 | 81.2 | |
| share of located proposals in a REAL cluster | 0.606 | 0.613 | 0.581 | |
| REAL clusters hit by this arm only | 13 | 8 | 117 | |
| judged harmful (bad fix + meaning changed), 15 sampled per run | 29/270 (0.107) | 27/270 (0.100) | 34/270 (0.126) | form <= current + 0.02: met |
| cost, time per run | $1.93, 6.7 min | $1.82, 6.3 min | $2.29, 7.9 min | form <= 1.3 x current: met |
| checker OK on the delivered report | 35/36 (fresh + guard) | | | reported |

Reference set: 1,350 clusters over both rules; under the character rule 395 of 877 clusters judged REAL
(per draft 53/127, 72/146, 86/198, 59/131, 59/126, 66/149).

## Guard, W1's six planted drafts, form x 3

| measure | form | bar | |
|---|---|---|---|
| plant recall (strict span rule) | 84/87 = **0.966** | >= 0.881 | met |
| intensifier recall | 18/18 | >= 15/18 | met |
| judged harmful of 270 | **27** | <= 15 | **missed by the letter; judge drift, see below** |

The three misses are 134 `term`, as in W1 and W2: every run names "codebook" inside a paragraph-level
naming finding anchored at the bank's definition, not within 2 lines of the plant. By content, 87/87.

## The harm guard and judge drift

The guard bar (15) was set from W1/W2's precision-judge counts (W2 reduced: 14). Re-judging **W2's own 18
prompts, unchanged**, with today's judge gives **30 of 270** harmful (originally 14). The same Sonnet judge,
same prompt, labels twice as many proposals harmful as on 2026-11-05/06. W3's 27 is below today's 30 for the
arm the bar came from, so the miss reflects judge drift, not the variant. The bar is still reported as
missed. Lesson: a bar taken from a judge's count on an earlier day needs that day's arm re-judged
beside the new one.

## Reading

- **The form is executed and changes nothing.** 35 of 36 delivered reports pass the checker. The one that
  doesn't passed it (OK 14/14), then re-rendered with a different margin width, which rewrote the report
  without the checklist. Runs answered 0 to 5 categories with `none`, each naming the sections checked.
  Asking the agent to account for every category did not move what it found or how reproducibly it found
  it: the per-draft differences are within ±0.09 and split 4/2.
- **The skill costs coverage.** On unplanted real drafts, both skill arms hit about 0.44 of the defects
  the pooled runs found, against 0.68 for the bare agent. The bare agent's extra proposals are real as
  often as the skill's (0.58 vs 0.61), so the gap is volume. **It is not the gate's caps:** the skill
  ledgers hold 55 and 54 rows per run and the gate cut only 12 (form) and 17 (current) rows over 18 runs,
  about half of them for `cap`. The skill arms write fewer rows in the first place. Candidate causes, not
  yet read from the traces: "every style row cites a rule; no rule, no row", or the caps applied while
  writing rather than at the gate. W1 could not see this: its planted defects were one per type.
- **What the judge counts as REAL is lenient by design** ("a careful copy editor would change it", errors
  or clear clarity problems). A reader who wants fewer, surer edits would weigh precision more, and on
  precision the arms are close (harmful 0.10 to 0.13). Test-retest agreement of the cluster judge on 80
  re-judged clusters: 0.80.
- This is the first protocol in the series where a form the agent must fill item by item did not move
  coverage or stability (cf. C2, R3, R5b). Those forms listed *objects in the paper* (budgets, figures,
  checklist items of a review); this one listed *defect categories*, which the agent already scans for.

## Caveats

- Cluster judge: 5 of 73 batches answered twice ("Wait — corrected:") and the first parser read both
  objects as one; the judge's last complete answer was used, from the saved raw output, with no new
  calls. All other batches had one object.
- Coverage is relative to the pooled reference set of the three arms; an arm proposing more hits more
  of it by construction. The REAL share and arm-only counts above are there to show what that volume is.
- 6 drafts; direction by draft is reported, no test of significance is claimed.

## Outcome

Outcome row "neither primary met": report, no merge; the traces show the form was filled honestly. Branch
`proofread-form` is kept unmerged. The measurement points at a different question for the researcher: the
published skill covers about a third fewer real defects than the bare agent on fresh drafts, because it
writes fewer rows, not because its gate cuts them.
