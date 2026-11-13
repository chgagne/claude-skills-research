# Second-pass subagent prompt

Send one subagent per section listed by `second-pass.py split`, all in one message so they run in
parallel. Fill the three paths; the rest is verbatim.

```
You are proofreading one section of an ML paper draft, with fresh eyes. Another reader has
already gone through the whole paper; your job is what they missed.

Read, in this order:
- <skill>/reference/critique-rubric.md        (what counts as a defect, the four levels)
- <skill>/reference/ledger-schema.md          (the row format and the anchor rules)
- <pass2>/sec-NN.anchors.txt                  (anchors already in the ledger: do not repeat them)
- <pass2>/sec-NN.tex                          (your section; read every sentence)

Write <pass2>/sec-NN.jsonl: one JSON row per defect you find that is not already covered by an
existing anchor, with every ledger field except `id` and `status` (style rows: `rule` is a
default key or `clarity: <why>`). Copy each anchor verbatim from sec-NN.tex, whole tokens, long
enough to be unique in the paper. Write a row for anything a careful copy editor at an ML venue
would change: errors, unclear or wrong wording, notation and symbols, captions or tables that
disagree with the text, claims the evidence does not carry. Keep every number, citation and hedge.
If you find nothing new, write one line {"none": "<what you re-read and checked>"}.
Reply with the number of rows written.
```

Then `python3 <skill>/assets/second-pass.py merge --ledger writing-ledger.jsonl` appends them with
new ids. It refuses until every section has its file.
