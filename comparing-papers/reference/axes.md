# The comparison axes

Each axis exists because a reviewer attacks it. This is what each one exposes, and what to
do when the two columns disagree.

## training_scale — the one that changes verdicts

**What it exposes.** A baseline retrained by the authors rather than taken from a released
checkpoint can be trained at a fraction of its published scale, and "the baseline is at
chance" is far more likely to be undertraining than architecture.

**The arithmetic.** `examples seen = updates × global batch size`. The tool shows its working
(`6.4M examples (100K updates x 64 batch)`) so you can check it against the appendix.

**Measured instance.** The draft trains every model for 10⁵ updates at global batch 64 — 6.4M
examples. SNIP states it is pre-trained on approximately 60M. The baseline saw ~11% of the
published scale, and the paper's most quotable result is that SNIP is *at chance*.

**What to ask for, in order:** evaluate the released checkpoint and report it as an extra row
(inference-only, cheap); failing that, state the gap explicitly and argue the comparison is
budget-matched by construction; at minimum, stop saying "at chance" without the qualifier.

## checkpoint — the cheapest possible rebuttal

If an official checkpoint exists and matches the paper's stated input constraints, evaluating
it is inference-only. A reviewer who knows the checkpoint exists will ask why it was not used,
and "we retrained instead" is a weak answer.

**This axis under-reports by construction.** Release information usually lives in a repository
or model card, not the manuscript. A *not found* here means "the paper does not say", which is
itself worth noting, but check GitHub before concluding no checkpoint exists.

## seeds — what the confidence intervals actually describe

One training seed plus bootstrap intervals over evaluation items means the intervals quantify
evaluation noise and say nothing about training variance. Three consequences follow, and all
three are things a reviewer will write down:

- no estimate of training variance exists;
- any claim about the *ordering* of ablation stages compares single runs;
- "significantly better in all N settings" refers only to evaluation-item resampling.

The fix is rarely all seeds: three seeds of the **baseline** is usually most of the argument,
because that is what the headline gap is measured against.

## compute — the trade the paper is making

Any method buying quality with extra compute must quantify it, or the trade-off — which is
the contribution — is unstated. Compare GPU type, count and hours, not just wall-clock.

## problem, data, metrics, results — pointers, not findings

These find *a* relevant sentence, not necessarily the best one. Use them to navigate:
"where does this paper describe its data" is a question the axis answers well, "do these two
papers use comparable data" is one only you can answer.

**Do not report a difference on these axes from the table alone.** Open both sources. The
tool has no notion of whether two dataset names refer to the same benchmark, whether two
metrics are computed the same way, or whether a number is directly comparable.

## Reading a `—`

`—` means no sentence matched that axis in the text that was fetched. It does **not** mean
the paper omits it. Check three things before reporting an absence:

1. Was the document degraded? Only an abstract was available, and appendix-level axes cannot
   be found in an abstract.
2. Does the paper use unusual vocabulary for it? The extractor matches phrasing, not concepts.
3. Is it in a table or figure rather than prose? Nothing here reads tables.
