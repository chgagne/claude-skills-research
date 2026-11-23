# Protocol S1: process skills on decision scenarios (first measurement)

Written 2026-11-22, before any scenario or rubric exists. Design settled with the researcher in an
interview the same day (journal `2026-11-22.md`, "Decision record: S1"): text decisions, 8 scenarios from
real incidents plus 8 written skill-blind, measured with no pass bar.

## Question

`running-cluster-experiments`, `using-drac-clusters` and `collaborating-on-research` are the three largest
skills (~400 lines each) and have never been measured. **Faced with a situation where the right next action
is known, does an agent with the relevant skill choose it more often than the bare agent?** This is a
baseline. It also builds the bench a later reduction would need.

## Scenarios

16 scenarios. Each is a short situation, given as 1-3 files in the working directory (a STATUS excerpt, a
log, `squeue`/`sacct` output, a diff, a config), with a prompt asking for the next actions. Nothing is
executed: no cluster is reachable and the tools are Read, Glob, Grep, Skill. The answer lists the exact
commands it would run, in order, and any message to the researcher, ending with one JSON block
`{"actions": [...], "message": "..."}`. The prompt never names a skill or hints at the trap.

- **Real (8)**, rebuilt by Claude from incidents recorded in memory and journals, where the right action is
  known from what happened. Names, accounts and paths are made generic.
- **Skill-blind (8)**, written by one subagent told not to read `~/.claude/skills/` or the memory directory.
  It gets only the three domains in a sentence each (running Slurm campaigns, working on Alliance clusters,
  long-running research collaboration with a supervisor) and writes 3 / 2 / 3 scenarios with their rubrics
  from general HPC and research practice.

Each scenario has a **rubric written and committed before any run**: a PASS condition (the action or
statement that must appear) and FAIL conditions (the actions that make it wrong, such as running the
analysis on a login node, or requeueing without asking). Every scenario names its target skill. The
researcher sees the list before any run.

## Arms and runs

| arm | what it is |
|---|---|
| `skill` | the scenario's target skill installed (frozen at the commit recorded in amendment 1) |
| `without` | the same agent, no skill |

claude-opus-5-5, 3 runs per arm per scenario = 96 runs, in one `--ablation with-without` call per scenario.
Gate 0.50/0.80.

## Measures

Sonnet judge, no tools, arm hidden: scenario files + rubric + the answer → `PASS` / `FAIL` with a one-line
reason. Each answer is judged twice, with a third call on disagreement. Reported:

- pass rate per arm, pooled, per half (real / skill-blind) and per skill, with per-scenario counts;
- paired difference (skill − without) per scenario, with a sign test over scenarios;
- skill invoked (Skill tool called) per run, and cost per run.

No pass bar (researcher's choice). The reading is descriptive: where the skill changes the decision, where
the bare agent already does it, and where both fail. That decides whether each skill is kept, reduced or
reworked, in a later interview.

## Cost

96 short runs at ~$0.15-0.30 ≈ $15-30; judge ≈ $3; scenario-writing subagent ≈ $2.
