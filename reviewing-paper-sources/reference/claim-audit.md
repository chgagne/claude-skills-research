# Claim audit

The point of this phase is to find the objection a careful reviewer will raise, and raise it first. Almost all of these come from arithmetic the paper did not do.

## Step 1: extract the headline numbers with their denominators

Build a small table of every quantitative claim: value, numerator/denominator, conditions, and where it appears. Papers restate their headline number in the teaser caption, abstract, contributions, table, results prose, discussion, and conclusion — seven appearances is common and is itself worth flagging as space waste.

If a rate appears without its denominator anywhere in the paper, that is a finding.

**Also read the abstract against the results section for strength, not just for
numbers.** Order the paper's assertions by the evidence each demands — *consistent
with*, *associated with*, *predicts*, *contributes to*, *improves*, *causes* — and
ask whether the abstract stands a rung or two above what the results section
actually establishes. "X gives rise to Y" in an abstract, supported by a
correlation in §5, is a finding, and it is the kind authors accept quickly because
the fix is one word.

**Do this by reading. Do not build a classifier for it.** One was built and
measured against four real drafts: it classified 2 of 30 abstract sentences as
asserting anything — 7% recall — and both detections were false. One matched
`outperforms` inside commented-out draft text; the other matched `outperform` in a
clause about two baselines, not about the contribution. The recall gap is not
fixable by a longer verb list, because strength is expressed in an open vocabulary
(*gives rise to*, *achieves*, *delivers*, *closes the gap*), and the precision gap
is not a vocabulary problem at all: **no lexicon can tell whose claim a sentence
is making.** Distinguishing the paper's assertion from a baseline's, or from a
sentence the authors deleted, is the whole task, and it is the reader's.

## Step 2: recompute

**Rule of three.** Observing 0 failures in *n* trials bounds the true rate at only **3/n** with 95% confidence.

- 0/54 ⇒ true rate could be up to 5.6%. It cannot demonstrate superiority over a published 3.5%.
- Sanity-check the other direction: if the true rate were the baseline's *p*, what is P(0 failures)? `(1-p)^n`. For p=0.035, n=54: 0.965^54 ≈ 0.15. A one-in-seven outcome is not evidence.

**Wilson interval** for small non-zero counts — 1/54 spans roughly [0.3%, 9.8%]. Report the interval, not the point estimate.

**Which comparisons survive.** Run the arithmetic against each baseline separately. Typically one comparison is significant and another is not, and the paper claims both.

**Denominator consistency.** A reported rate must be reachable from its own
denominator by an integer numerator. "94.3% of 54" cannot happen — 51/54 is 94.44%
and 50/54 is 92.59% — so either the rate, the denominator, or a count of excluded
items is wrong. It costs one division and it catches a transcription error nothing
else will.

Two cautions, both measured. First, **check the rate against *its* denominator, not
the nearest one.** A baseline's published rate sitting next to this paper's sample
size is the commonest trap: the arithmetic then refutes a pairing the paper never
claimed. Second, **most rates are not checkable this way at all** — across four real
drafts holding 187 percentages, only 2 stated a denominator close enough to pair
mechanically, and both of those pairings were wrong. A rate whose denominator the
paper never states anywhere is already a finding under Step 1, and that is the case
you will actually meet.

## Step 3: read the primary sources for every quoted number

Do not accept the submission's description of a baseline. Fetch the cited paper and extract the actual protocol. Recurring mismatches:

- **Model generation.** A 2023 GPT-3.5 number is not a fair target for a 2026 frontier model with no architectural contribution.
- **Aggregation.** A published rate may average over conditions (grammars, datasets, task types) with wildly different difficulty, some near-100% failure.
- **Sample size.** n=2280 vs n=54 is not a like-for-like comparison even when the percentages are comparable.
- **Attempts allowed.** Single-try baselines vs a method with three retries and a fallback.
- **Task selection.** If the system generates its own goal and then satisfies it, and takes one goal where the baseline took five, it selects its easiest task. This biases the result and is rarely acknowledged.

Build a protocol-comparison table with one column per system. The mismatches become self-evident.

**Fill every cell from text you actually retrieved, and leave it empty otherwise.**
Opening a DOI, seeing that a paper exists, and writing down the protocol you expect
it to have is not reading the primary source — it produces a table that looks like
evidence and is partly recollection. If the source could not be obtained, the cell
stays empty and the review says which baseline was not checked. An inferred protocol
is worse than a missing one, because a missing one invites the question and an
inferred one closes it.

## Step 4: look for metric saturation

Ask: **can this metric fail, given the architecture?** A pipeline whose terminal state is a deterministic fallback that succeeds by construction cannot fail a "does it succeed" metric. The reported rate then measures the fallback, not the contribution.

The fix to demand is always the same: the **outcome distribution**. How many runs resolved on the first attempt, on each retry, and via the fallback? Systems that log typed statuses already have this data.

## Step 5: count competing explanations for the result

List every mechanism in the system that could independently produce the reported outcome. If there are five and the paper credits one, the causal claim is unsupported and needs an ablation. Name the cheapest decisive ablation and estimate its cost — a concrete, affordable experiment is far more useful than "an ablation is needed".

## Step 6: check what is *not* evaluated

- Modes, paths, or intents described at length but exercised by no experiment
- Contributions claimed in the intro with no corresponding evaluation (interfaces are the usual case)
- Repetitions: one run per item gives no variance. Ask for ≥3.
- Missing setup: model identifiers and dates, temperature, seeds, library versions, corpus provenance, subset-selection rules

**Selection rules stated after the results are post hoc.** If a subset or an excluded failure case is justified only once the number is known, say so. The fix is to state the rule before the numbers, which is free if the rule was genuinely fixed in advance.

## Step 6b: check the baseline's training scale against its own paper

When the baseline is *retrained by the authors* rather than taken from a released checkpoint, compute what it actually saw and compare with the published figure:

```
examples seen = updates × global batch size
```

Then find the baseline paper's pre-training scale. A baseline retrained at a fraction of the original scale can manufacture the paper's most quotable result — "the baseline is at chance" is far more likely to be undertraining than architecture. Also check whether an official checkpoint exists (release notes, GitHub, model naming that matches the paper's stated input limits); if one does and was not evaluated, that is the first question a reviewer asks, and it is usually inference-only to answer.

Report the ratio explicitly. "6.4M versus ~60M examples, so ~11%" is an argument; "the baseline may be undertrained" is not.

## Step 6c: seeds

Search the appendix for the seed count. `"trained from scratch with training seed 0"` plus bootstrap CIs over evaluation items means:

- no estimate of training variance exists;
- any claim about the *ordering* of ablation stages is a comparison of single runs;
- "significantly better in all N settings" refers only to evaluation-item resampling.

Cost the fix from the paper's own reported GPU-hours so the recommendation is actionable, and say which single run would buy the most (usually 3 seeds of the baseline, since that is what the headline gap is measured against).

## Step 7: cost

Any method that buys quality with extra compute must quantify it: LLM calls, tokens, wall-clock, dollars per unit of output, against the single-pass baseline. Without it, the trade-off — which is the entire contribution — is unstated.

## Checklist: findings that recur

These are worth checking on every quantitative systems paper:

| Check | Why |
|---|---|
| Sample size behind a 0% / 100% rate | Rule of three: 0/n bounds the rate at only 3/n. 0/54 cannot beat a published 3.5%. |
| Protocol match to each baseline | Different models, goals per item, or corpora make the comparison decorative. |
| Self-built baselines | A baseline the authors wrote can carry the whole result — and its failures may be its own bugs. |
| Ablations for the claimed mechanism | "X is the primary mechanism" needs X removed. Count the competing explanations. |
| Metric saturation by construction | A fallback that always succeeds makes a success-rate metric unfalsifiable. Demand the outcome distribution. |
| Unevaluated contributions | Interfaces claimed as contributions with no study, walkthrough, or case study. |
| Cost of the proposed method | Reliability bought with compute is a trade, not a win, until quantified. |
| Selective citation | Read the cited paper's own caveats. Citing only its favourable half is a real finding. |
| Baseline training scale vs the published model | Read the baseline paper's *pre-training* scale and compare with `updates × batch`. A retrained baseline at 10% scale can manufacture a "baseline is at chance" result. Check whether an official checkpoint exists. |
| Seed count | "Trained with seed 0" plus bootstrap CIs over evaluation items means no training-variance estimate. Ablation orderings are then unsupported. |
| Selection on the reported construct | Hyperparameters chosen on "held-out <the headline metric>" need an explicit disjointness statement. |
| Per-item denominators inside an aggregate | A rank or rate averaged over categories can hide categories with 2 alternatives. Get the per-category $n$ from the appendix. |

**Read the commented-out text.** `grep` for `^\s*%` blocks in the section files. Authors delete their own caveats under page pressure, and a caveat they wrote and cut is the strongest possible recommendation — you are asking them to restore their own sentence, not accept yours. In one paper this surfaced both a deleted single-seed disclosure and a co-author's unactioned note about a missing citation. Also check whether the paper's own editorial macros (`\todo`, initials macros) are still defined and whether any are live.

