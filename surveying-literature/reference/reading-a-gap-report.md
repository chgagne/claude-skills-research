# Reading a gap report

A gap report is a queue of things to check, not a list of failures. Most of it is noise by
construction — the sweep casts wide and grades hard so that the top of the list is short.

## What each grade obliges you to do

**`THREAT`** — on the contribution *and* reached from more than one direction. Each one needs
a response **in the paper**, not just an acknowledgement:

- cite it and state the difference in one sentence, or
- narrow the novelty claim so it is true alongside this work, or
- establish it is not actually the same thing, and move on

The failure mode this prevents is a reviewer writing "the authors appear unaware of X",
which costs more than the citation would have.

**`RELATED`** — topically close, or multiply reached. A one-line citation in related work.
Under page pressure, cite the two or three that a reader of this area would expect and drop
the rest.

**`BACKGROUND`** — reached once, no topical overlap. Skim the titles; act on nothing unless
one is obviously important. If several look important, the angles were too narrow — re-run
with more.

## Read the Coverage section first

The grades mean nothing if the sweep only saw half the bibliography.

- **Unresolved seeds** are cited works no index could resolve. Anonymous artifacts, blog
  posts and some workshop papers legitimately land here. Four unresolved out of eighteen
  means four branches of the citation graph were never explored.
- **Degraded sources** (exit code `2`) mean an engine was rate-limited or down. Re-run
  before concluding anything; OpenAlex's budget resets at midnight UTC.
- `n/r` in the Cites column means no engine reported a count, not that the paper is uncited.

## Why a paper surfaced matters as much as that it did

The "Why it surfaced" column lists discovery paths:

- `topical` only — found by searching your own topic. This is where **parallel work** lives:
  papers solving your problem without sharing your citations. The most dangerous omissions
  are here, because nothing in your bibliography points at them.
- `backward` only — an ancestor of something you cite. Often genuinely background.
- `forward` — someone built on a paper you cite. Recent ones are worth a look; they may have
  done your extension already.
- Several paths — the strongest signal, and why multi-path membership is required for
  `THREAT`.

## Do not trust the ranking to know what matters

The score combines topic overlap, how many ways a paper was reached, citations per year, and
recency. It has no notion of quality, venue prestige, or whether a claim is correct. It
cannot tell that a highly-ranked paper is a workshop abstract or that a low-ranked one is the
canonical reference.

Read titles, not scores. The ranking is there to put the plausible candidates in the first
twenty rows, not to make the judgement.

## When the report is empty or useless

- **No candidates**: the draft's citations could not be resolved, or every neighbour is
  already cited. Check Coverage before reading it as a clean bill of health.
- **Everything is `BACKGROUND`**: no angle matched anything. Run `--seeds-only` and look at
  the angles — if they read like sentence fragments rather than topics, the draft's
  contribution sentences are the problem, and the title and abstract are doing the work.
- **Hundreds of `RELATED`**: the angles are too generic. A three-word topic phrase is the
  sweet spot; two words returns the whole field.
