# Results R4: count-claim check (stopped at calibration)

2026-11-09. Protocol: `PROTOCOL-R4.md` (+ amendment 1). Material in `private/r4/`.

## Verdict

**R4 stops before the check is built, as pre-registered: the bare agent catches planted count
slips 16 of 16 times.** In R1 stage 3, both arms missed two real count slips ("seven depths"
followed by six values; "all eleven" in a paper that scores thirteen). On 8 planted slips of the same
two shapes, in 8 fresh disguised drafts, the bare agent found every one in both runs. So the stage-3
misses do not show a weakness for this type of defect, and a count-claim script has nothing
measurable to add. No candidate was built, and no test or real-set guard was run.

## Numbers

Bare agent (claude-opus-5-5, R3's review prompt, no web), 8 dev plants × 2 runs:

| shape | plants | found |
|---|---|---|
| count vs the list it introduces ("Four rules" + three listed; "four phases" + three named) | 2 | 4/4 |
| count vs another count elsewhere ("six convolutional layers" vs the appendix's five; "42-participant" vs 48; "six settings" vs "five variants"; "on five tasks" vs a four-task list; "four held-out cases" vs "the three cases"; "six segmentation models" vs five) | 6 | 12/12 |

Judge: 0 flips in 16. All 16 evidence quotes were read: each names both places and the true count
("Sec. 2.1 says 'consists of four phases' and then lists three"; "Contribution 4 says six; the
abstract, Tab. 4 and the conclusion all have five"). $0.97 per run, 25.9 issues per run.

## Reading

The stage-3 misses look specific rather than systematic. "Seven depths" was followed by six values
inside a parenthesis of numbers in a long results paragraph. "All eleven" sat in a Limitations
paragraph, against a total of thirteen that is never printed as a single count next to it. The
plants, even the far ones, put the contradicting count in a sentence that reads as a count. A
real-paper miss rate of 2 in 12 is about the bare agent's residual error on real material; planting
the shape does not reproduce it. This is the same pattern as P1, X1, X2 and R1: single defects
made to order sit at the bare agent's ceiling.

The R1 line of work (planted, documented, count-type) is closed. The test plants (8, never run)
are kept unused in `private/r4/plants.json`.

Cost: 16 runs, $15.5.
