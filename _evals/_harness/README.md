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

Found by the surveying-literature smoke runs (2026-10-09), and missed by the first two
verifying-bibliography evaluations:

- **A run's sandbox gives Bash no network.** Every host a skill's script calls must be granted
  with `--allow-tools "WebFetch(domain:<host>)"`; the grant applies to Bash too. Grant the same
  hosts to every arm. Without it, scripts fail with "deny network-outbound <host> (user denied)"
  and the agent silently falls back on WebFetch, so the arm no longer measures the skill.
- **A run's fresh HOME has no `~/.claude/skills/_shared`**, which every scholarly skill imports.
  The case's scaffold script must install a frozen copy (`--scaffold`).
- **Files and secrets do not reach a run.** `context.add_dirs` copies nothing; the scaffold copies
  inputs from the case directory into the working directory. Secret-looking variables
  (EVAL_S2_API_KEY) arrive empty; the scaffold installs a 0600 key file in the run's HOME instead.
  `scaffold_script` is a path to a file, not inline shell. `case.yaml` needs `execution.prompt`.
- **Check that the script ran**, not that the run passed: read the tool results in the trace.
