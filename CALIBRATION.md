# Calibrating a checker

A finding rate means nothing without a false-negative rate beside it. This is the
protocol these skills use when a rule needs measuring rather than arguing about.

It contains no data. The gold sets live outside this repository, because they are
built from unpublished drafts.

## The protocol

1. **Build the gold set before running anything.** Each item carries the label a
   careful human assigned, and the reason. Store the labels where the run cannot
   read them.
2. **Freeze the rule and write down what "firing" means.** The commit, and the exact
   lexicon, threshold or pattern values. A criterion decided after the results are in
   is not a criterion.
3. **Run 3–5 independent replicates.** Independent means each starts from the source
   material, not from another replicate's output.
4. **Freeze every verdict before opening the labels.** This is the whole protocol. A
   single glance at the gold labels mid-run turns a measurement into a tuning
   exercise, and nothing downstream can recover the difference.
5. **Report both error directions with an interval,** plus the replicate
   disagreement rate. A rule whose replicates disagree is not measured, whatever its
   mean accuracy.
6. **Bind the result to the frozen rule.** Changing the lexicon, the threshold or the
   matching logic invalidates the measurement. It does not carry over, and a
   calibration figure quoted after a rule change is worse than none.

## Why it is written this way

Every step exists to stop one failure: a rule tuned until it agreed with the labels,
then reported as though it had been measured against them.

The two dangerous moments are both moments of good intentions, and both were hit
while measuring the rules that shipped in August 2026:

**Redefining the criterion once the data is in.** One probe's criterion required a
*critical* finding. The corpus offered a *major* one tagged "desk-reject risk", which
would have satisfied the spirit of the test and produced a satisfying result. Reading
the label loosely after seeing the data is how a null result becomes a positive one,
so the probe was recorded null. Step 2 exists to make that call cheap: the criterion
is already in writing, so the only question is whether it was met.

**Repairing the instrument mid-run.** Another probe reported a 100% hit rate on first
run — six of six. That is a detector symptom, not a corpus symptom, and it traced to a
regex reading a percentage total as a sample size. Fixing it was correct. But note
what happened: the instrument changed *after* its output had been seen, so the
pre-fix measurement is void, and the post-fix run is a new measurement of a new rule.
Step 6 is what forces that bookkeeping. The honest sequence is: fix, re-run, report
the post-fix number, and say that an earlier version reported differently.

The distinction between those two is worth holding onto. Repairing a broken instrument
is legitimate and necessary; silently carrying its earlier output forward is not.

## Status

The protocol is written from the experience of measuring six rules by hand, not from a
completed replicated run — no rule in this repository has yet been through steps 3–5
as specified. Treat it as the discipline to follow next time, and expect the first
real application to change it.

## Where the gold sets live

Outside this repository, alongside the acceptance suites that are also kept out of it.
A gold set built from unpublished drafts cannot be published, and the protocol is the
reusable part anyway.
