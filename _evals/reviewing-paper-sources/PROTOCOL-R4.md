# Protocol R4: a count-claim check the reviewer must answer

Written 2026-11-09, before any plant, script or run. Design settled with the researcher in an
interview the same day (journal `2026-11-07.md`, "Decision record: R4").

## Question

In R1 stage 3, both arms found every documented inconsistency that had arithmetic or a table
behind it, and both missed the same two: a **bare count word that disagrees with an enumerated list
or another count** ("seven depths" followed by six values; "all eleven" models in a paper that
scores thirteen). C2 showed that a list the agent must answer item by item is executed, where prose
guidance is not. R4 asks whether a script listing every count claim with its possible
contradictions, which the review must answer, lets the skill catch these slips.

## The candidate (branch `count-check`, written after calibration)

`assets/count-claims.py paper.tex` lists every claim of the form *number-word or numeral + plural
noun* ("seven depths", "13 models", "all eleven", "twelve binary scene factors"). Each claim is
paired with what could contradict it:
(a) the length of an enumeration that follows within the same sentence or display (comma lists,
value lists, itemize), when there is one;
(b) every other count of the same noun (lemma) elsewhere in the paper;
(c) the row or column count of a table the sentence references, when it is mechanically
recoverable.
The review form gets one row whose answer is the script's list, each pair marked consistent /
**inconsistent** / not comparable, with an inconsistent pair becoming an issue. Only this is added
to the current skill (frozen at the commit recorded when test cases are built).

## Material

**Drafts.** The 8 disguised, memory-probed C2-pool drafts never used in R1–R3: 115, 133, 135,
140, 148, 153, 156, 161 (unplanted originals).

**Plants.** Two per draft, in different sections: a **dev** plant (calibration and script
development) and a **test** plant (test only, never seen during development). A plant edits one
count word or numeral (at most one line) so that it disagrees with an enumeration it introduces, or
with another count of the same thing stated elsewhere. Neither side is otherwise changed. Valid
only when Claude has checked and recorded: (a) the count is now wrong on the draft's own evidence
(the list length or the other count); (b) the counterpart is unambiguous (same noun, same object);
(c) the edit is not arithmetic or a table cell (those are already found); (d) no tells (the edit
does not break grammar, e.g. "one models"). Proposed by one subagent per draft from a fixed
prompt; checked by Claude.

**Real set (guard).** R1 stage 3's 8 papers plus the reserve 2607.24016: 18 documented defects,
v1 sources unchanged.

## Calibration (bare, dev plants)

8 dev plants × 2 bare runs = 16 runs (R3's review prompt, no web). Keep the plant type if bare
recall ≤ 0.70. Otherwise R4 stops before building the candidate: the stage-3 misses were then
specific to those papers, not to the type.

## Test

Arms: `candidate` (skill + count check), `current` (skill as frozen), `without` (bare). 8 test
plants × 3 arms × 2 runs = 48 runs. Guard on the real set: candidate and current, 9 papers × 2 runs
= 36 runs. Same tools, limits, gate and file capture as R1 stage 3.

**Scoring.** Sonnet judge, run twice with a tie-break, as in stage 3 (FOUND: the review names the
count and what it contradicts). Claude reads every FOUND quote and searches misses for the
key terms. Other issues per run are counted. For the false-issue guard, the candidate's issues
that came from the count table (marked inconsistent) are each judged REAL / FALSE against the
draft by the same judge.

## Criteria

1. **Primary:** test-plant recall, candidate − current ≥ **+0.15**.
2. **Guard (noise):** FALSE count-table issues per run ≤ 1.0, and total issues per run ≤ 1.5 ×
   current.
3. **Guard (real set):** candidate recall on the 18 real defects ≥ current − 1 defect-run.

All three met: merge `count-check` with a measured line. Primary met but a guard missed:
report, and decide with the researcher. Primary not met: report, with no merge.

## Cost

Calibration ~$20. Test ~$75 (48 runs). Real-set guard ~$60 (36 runs). Judge under $10. Plant and
script building: subagents.
