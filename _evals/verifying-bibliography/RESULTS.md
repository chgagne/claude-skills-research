# Stage 1 results (2026-10-09)

Protocol: `PROTOCOL.md`, committed at 3a873fd before the first scored run.
36 runs, `claude-opus-5-5`, no format failure, no contaminated trace, no run error.
Scores: `results/stage1-2026-10-09.json`.

| Arm | Recall | False positives | Label accuracy | Cost per run | Time per run | Turns |
|---|---|---|---|---|---|---|
| without | 14/14 x 12 runs = 1.00 | 0 / 288 | 1.00 | $0.18 | 20 s | 2.8 |
| skill | 1.00 | 0 / 288 | 1.00 | $0.52 | 60 s | 18.5 |
| self | 1.00 | 0 / 288 | 1.00 | $0.54 | 369 s | 19.5 |

## Verdict under the protocol

Criterion 1 fails: the skill's recall gap over both other arms is 0 points, not 20.
Criterion 2 holds trivially (no arm has a false positive). The stage-2 trigger is not met.
The pre-registered reading is **not a success**.

## What the result actually measures

It does not show that the skill is useless. It shows that this case set cannot tell the
arms apart. Every arm is at ceiling, and the without arm reached it from memory: 2.8 turns,
14 Bash calls across 12 runs, two runs with at most one tool call. The cases use famous
papers (ResNet, BERT, AlphaGo, LSTM, NSGA-II), whose real metadata the model knows by heart,
so a planted defect is recognisable without looking anything up. The skill arm, by
contrast, ran its script 16 times and fetched 117 pages, at three times the cost and time.

On this material the skill costs 3x and buys nothing. That is a real finding about famous
references, not about the bibliographies the skill was built for: its motivating cases were
long-tail papers that a title search and the model's memory both get wrong.

The DBLP anti-bot page recorded before the run did not show up as missed preprints: every
arm caught all three, which is again what memory alone gives on famous papers.

## What a discriminating stage needs (a new protocol, not a stage 2 of this one)

- Long-tail references: workshop papers, small venues, theses, non-ML journals, and works
  published after the model's training cutoff, where memory cannot stand in for lookup.
- A memory-only probe per case before running the arms: any defect the bare model flags
  with no tool call is too easy and is replaced.
- Subtler defects: one page digit, author order, a year off by one, a preprint published
  only recently.
