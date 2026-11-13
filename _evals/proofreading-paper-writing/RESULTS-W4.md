# Results W4: an open defect criterion in place of "no rule, no row"

Protocol: `PROTOCOL-W4.md` (18cfe81; amendment 1 e226443, frozen material hash 76a39f4d). 54 runs,
2026-11-12 09:46 to 20:16 at the standing 0.50/0.80 gate, none failed, every final message carried a
parsable JSON block. All judging for all arms in one session (2026-11-12 20:17-20:25). Scoring:
`private/w4/score_w4.py score` (sha256 prefix 625444a0a4dc).

## Verdict

**Coverage criterion not met; precision guard met. No merge.** The open criterion recovers about half of
the gap between the published skill and the bare agent: `open` covers 0.547 of the judged-real defects,
`current` 0.435, the bare agent 0.653. The bar was `open` >= bare - 0.05; `open` is at bare - 0.106. It does
so without more harmful edits (judged harmful 0.081, bare 0.093, current 0.078).

## Arms

| arm | what it is |
|---|---|
| open | proofreading-paper-writing at `proofread-open` 9aeeff2: copy-editor criterion, `clarity: <why>` rules, rubric widened (notation, ambiguity, imprecise word, caption vs text, claim vs evidence) |
| current | the published skill |
| without | same agent, same prompt and tools, no skill |

## Results, 6 new fresh post-cutoff drafts x 3 runs per arm

| measure | open | current | without | criterion |
|---|---|---|---|---|
| coverage of judged-REAL clusters (character overlap) | **0.547** | 0.435 | 0.653 | open >= without - 0.05: **-0.106, not met** (bare higher on 5/6 drafts) |
| judged harmful share, 15 sampled per run | **0.081** (22/270) | 0.078 (21/270) | 0.093 (25/270) | open <= without: **met** |
| open - current, coverage | +0.112 (open higher on 5/6 drafts) | | | reported |
| coverage, line rule | 0.701 | 0.602 | 0.787 | reported |
| agreement across runs, line / character rule | 0.823 / 0.696 | 0.796 / 0.664 | 0.829 / 0.695 | reported |
| REAL clusters hit by this arm only | 32 | 16 | 96 | reported |
| proposals per run | 71.0 | 58.6 | 84.9 | |
| per run: mechanics / style / flow / framing | 28.8 / 26.4 / 2.9 / 12.8 | 30.3 / 13.8 / 3.7 / 10.9 | 41.9 / 19.4 / 5.7 / 17.9 | |
| math/notation proposals per run (keyword sort) | 3.1 | 2.8 | 12.1 | |
| cost per run | $2.15 | $1.89 | $2.29 | no bar |

Reference set (character rule): 470 of 910 clusters judged REAL. `current` vs bare reproduces W3 on new
drafts (0.435 vs 0.653; W3 0.438 vs 0.684).

## Reading

- **The mechanism W3's trace reading proposed is real, and it explains about half the gap.** Lifting
  "no rule, no row" doubles style rows (26 vs 14 per run, now above the bare agent's 19) and raises
  coverage by 0.11 at the same harm rate.
- **What remains is mechanics and notation.** Of the 111 REAL clusters bare hits and `open` misses, 42
  are mechanics and 45 framing; 31 involve math or notation. `open` writes 29 mechanics rows per run against
  the bare agent's 42, and 3 math/notation proposals against 12, although the rubric now names notation.
  The gate still cuts little (22 rows over 18 runs: 15 taste, 7 cap), so the volume is again set while
  writing. A likely contributor, not tested: the skill renders a math fix as a margin comment rather than a
  tracked change (several runs say so in their hand-back), which makes such rows feel second-class.
- The precision cost of the extra rows is nil on this judge: harmful share 0.081 vs 0.078 for `current`.
- The judge was not compared with W3's judging day; all three arms here were judged in one session, as the
  protocol requires.

## Caveats

- `judge.sh` was changed after the freeze, before any judging, to take the judge's last complete answer
  when a batch answers twice (W3 resolved 5 such batches the same way by hand). The prompts are unchanged.
- Coverage is relative to the pooled reference set; volume and arm-only counts are reported beside it.
- 6 drafts; direction by draft only.

## Outcome

Outcome row "coverage not met": report, no merge; traces read (above). Branch `proofread-open` is kept: it is
a measured improvement over the published skill (+0.112 coverage, same harm) that misses the bar the
researcher set against the bare agent. Whether to merge it anyway, push further on mechanics and notation,
or close is the researcher's call.
