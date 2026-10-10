# surveying-literature, protocol B: the revised skill on the same frozen test set

Written 2026-10-10, after protocol A and the dev-set loop, before any protocol-B run.

## What changed since protocol A (decided on the dev set only)

- Retrieval: a throttled Semantic Scholar key is retried anonymously (bf62212).
- Script variants (`--seedset`, `--rank coupling`, `--angles`) moved dev recall by noise only;
  defaults unchanged.
- A script-first workflow (ab82b80) gave no dev gain (key non-memory 0.111 vs 0.111).
- **The tested change:** SKILL.md makes the gap sweep a search method (12 targeted queries run with
  WebSearch, candidates vetted, ranked by closeness to the contribution), the script optional.
  On the dev set it recovered 14/46 non-memory references at @30 against 6/46 for the bare agent.
  Frozen at commit **d6d64fa**. Its workflow section is identical to the dev-tested text; one
  informational sentence about the dev result was added under "Measured result".

## Arms and setup

**skill-B** (`surveying-literature` at d6d64fa) and **without**, run together in one
`claude plugin eval --ablation with-without` call, 3 runs per paper, so both arms share the same
time window. Everything else as protocol A: the same 20 frozen test drafts and gold labels,
prompt, tools, model `claude-opus-5-5`, 80 turns, 40-minute timeout, scaffold, Bash network
grants, OpenAlex off, at most 2 runs at a time. Protocol A's runs are not reused.

## Scoring and criterion

Unchanged from protocol A (`analyze.py` at its committed version, contamination rule as written
and as implemented after protocol A): primary Recall@30 on non-memory key prior work. The revised
skill succeeds if its primary recall exceeds the without arm's by at least **15 points** and its
already-cited share is not higher. Reported beside it: all non-memory references, memory-reachable
ones (the dev set showed a drop there), cost and time, and the comparison with protocol A's arms.

## Infrastructure failures

A run that ends on an account or session limit is an unobserved run: every run of any affected case
is redone in both arms, as in protocol A.
