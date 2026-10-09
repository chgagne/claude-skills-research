# Eval harness

Shared by every skill evaluation under `_evals/`. Each evaluation keeps its own cases,
gold labels, scorer and protocol; this directory holds what they have in common.

- `extract.py` turns `claude plugin eval --json` output into one JSONL row per run (arm,
  case, final message, full trace, cost, time). Needs `--keep-temp`, because the traces live
  in the kept run directories.
- `probe.py` runs the memory probe: the bare model, no tools, no skill, N times per prompt.

Lessons the harness encodes, from the verifying-bibliography runs:

- `--case` in `claude plugin eval` filters on the case's `name:` frontmatter, not its directory.
- There is no script grader; use a trivial regex grader and score offline from the traces.
- Runs get a fresh HOME and only `EVAL_*` variables. The shared retrieval layer reads
  `EVAL_S2_API_KEY` and `EVAL_SCHOLARLY_DISABLE` for that reason.
- A high score without the skill is not evidence of a memory leak when the agent has web
  tools. Leakage is measured by the no-tool probe and by the trace, never by the score.
