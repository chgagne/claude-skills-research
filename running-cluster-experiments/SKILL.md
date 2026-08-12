---
name: running-cluster-experiments
description: Use when planning, budgeting, submitting or resuming a multi-job experiment campaign on a Slurm/HPC cluster — sizing walltime, shaping jobs and arrays, deciding what to submit first, or after a job hit its walltime, produced no results, silently ran the wrong configuration, or got the wrong number of GPUs.
---

# Running Cluster Experiments

## Overview

This is the **methodology** of experiment campaigns on shared clusters. For the
mechanics — MFA, account strings, gres names, quotas, partitions, rsync flags —
**REQUIRED BACKGROUND: use `using-drac-clusters`.**

**Core principle: a scheduler will kill your job at an arbitrary point, and a
cluster will hand you less than you asked for. Design for both, or your
allocation buys nothing.** Every rule below is a consequence.

The expensive failures are never "the code crashed". They are: the job ran
perfectly and wrote nothing; the job ran a different experiment than its name
says; the allocation was spent before the first useful instruction.

## Never compute on a login node — use an interactive allocation

Login nodes are shared by hundreds of people and staff kill offenders. `squeue`,
`ls`, `sacct`, `diskusage_report`, editing, `sbatch`, file transfer: fine.
**Anything that loops over data, parses a large file, trains, plots, or runs for
more than a few seconds: not fine** — including "just this once to check
something", and including work you started before realising how big it was.

There is always an alternative, so there is never an excuse. **Interactive
compute is a normal allocation, not a special favour:**

```bash
salloc --account=<alloc> --cpus-per-task=4 --mem=16G --time=1:00:00   # shell on a compute node
srun --jobid=<id> --pty bash                                          # shell inside a running job
```

Short interactive requests usually start in seconds — a measured example: a
1-hour CPU job and a 30-minute GPU job on a busy cluster both began within ~2
minutes, while an 8-hour job on the same cluster waited 13 hours. **Asking for
less gets you compute faster than not asking at all.**

If interactive scheduling is genuinely slow, the answer is `sbatch`, not the
login node.

## Build a cost model before you choose a walltime

**Measure per-unit cost at the real configuration, on the machine that will run
it, then multiply.** Not at a smaller model, not at a shorter run, not on a
different cluster, not from last quarter's estimate.

Budgets die three ways. Each later one survives a calibration careful enough to
defeat the earlier ones.

**1. Extrapolating across scale.** A `--time` budget carried a comment grounded
in a careful 7B-model calibration; the same code at 32B cost **~170 s/generation
instead of ~37 s** — the job needed 9 h and asked for 8. The calibration was
honest and the arithmetic was right. The model changed underneath it.

**2. Extrapolating across units — measuring *a* unit instead of the *worst*
one.** A campaign of 12 cells over 4 datasets was calibrated on one cell: 136
s/generation, corrected for trend, projected 4.6 h, walltime set to 8 h. That
projection was *correct* for its dataset — the three cells of it finished in
4:18, 4:38 and 4:55. A different dataset in the same campaign ran at **385
s/generation and was killed at generation 74 of 100**, needing ~11 h. It wrote
nothing and cost 16 GPU-hours. Within that slow dataset, one seed finished in
7:01 while another projected 10.7 h — **so even the dataset was not the right
unit of cost.**

**3. Extrapolating across machines — and agreement between two of them proves
nothing about a third.** A single-threaded CPU workload was measured at **179
ms/unit on a laptop** and, independently, at **179 ms/unit on cluster A**. Two
machines, two separate measurements, exact agreement. On cluster B the same code
ran at **459 ms/unit — 2.6x** both anchors. Nothing was wrong with either
measurement; per-core performance simply differs between clusters, and CPU-only
work has no GPU to hide behind. The agreement felt like corroboration and was
only a coincidence of two similar machines.

- **Measure on the cluster you will submit to.** A rate carried over from another
  cluster is an estimate, not a calibration, however carefully it was taken.
- **Two agreeing anchors are not a trend line.** Independent measurements
  agreeing raises your confidence in *those* machines and tells you nothing about
  a third. Treat cross-machine transfer as unmeasured until measured.
- This applies hardest to **CPU-bound** work, where the node's cores are the
  whole story. GPU work is often dominated by an identical accelerator and
  transfers better — but the CPU-side client, data loading and startup do not.
- **Margin computed against an untrusted anchor is not margin.** In that same
  campaign the walltime was set to what looked like ~10x the projection. Measured
  against what the tasks actually did, the real headroom was **1.5x** — the
  slowest task used 68% of its budget. The request survived because it was sized
  generously on principle, not because the projection was good.

- **Time the MOST EXPENSIVE unit, not a convenient one.** If you cannot tell
  which that is in advance, time one per stratum (per dataset, per model, per
  problem size) — the strata are exactly the axes you expect cost to vary along,
  which is usually the axes your experiment varies.
- **Then add margin for variance *within* a stratum**, which is separate from
  and can rival the variance between strata.
- **Watch the trend, not the mean.** Per-generation cost rose 140 s → 204 s as
  one run progressed; measured over 7 generations vs 100, the early mean
  underestimated by a factor of 1.20. Correct for it explicitly.
- **The underestimate grows with the extrapolation distance.** Same code, same
  cell, same machine, cost per unit at three run lengths: **459 ms at 100 units,
  564 ms at 1,000, 678 ms at 10,000.** Budgeting the longest run from the
  shortest run's rate underestimates by **1.48x**; from the middle run's rate, by
  1.20x. When a workload's cost is a function of its own accumulated state, a
  short calibration is not a cheap approximation of a long one — it is a biased
  one, and the bias scales with how far you extrapolate.
- **Set the walltime per stratum, not globally.** When one stratum needs 2x the
  others, give the longer walltime *only to that stratum*. Raising it for
  everything makes every task queue worse to protect a minority — and on a
  bucketed scheduler it can push the whole campaign into a scarcer partition.
  **An array shares one `--time` across all its tasks, so this means one array
  submission per stratum**, not one array over the whole grid. Sizing every cell
  to the worst stratum is the convenient choice and the wrong one.
- **Record the measured rate next to the `--time` line**, with the configuration
  AND the unit it was measured on. "4.6 h/cell" is a trap; "4.6 h/cell on
  dataset X, 11 h on dataset Y" is a budget.
- Round `--time` *down* into a partition bucket (see `using-drac-clusters`), but
  never below the measured cost.

### Fixing a walltime after submission

`scontrol update JobId=<id> TimeLimit=<new>` on a PENDING job **is accepted but
does not re-route its partition.** Raise the limit past the current partition's
cap and you get a job that is legal, eligible, and unschedulable in the queue it
is sitting in — visible only as an ordinary `(Priority)` wait. Cancel and
resubmit instead, so the normal time-based routing runs again. Check the caps
first:

```bash
sinfo -h -o "%P %l" | sort -u
```

## One resource class per job

**Do not co-locate work with different resource profiles in one job.** Split by
what each part actually needs.

A concrete failure: three experimental arms ran in one GPU job. The `classic`
arm needed no GPU at all — 0.18 s/generation of pure CPU arithmetic — and held
two H100s while it ran. The two LLM arms needed ~4.2 h and ~4.8 h, so no sane
walltime fit all three. Split apart: the CPU arm finished in 10 minutes on a CPU
node, and each GPU arm became an independent short job.

Splitting also buys **queue position**, which is usually the scarcest resource:
several short jobs start far sooner than one long job, and a killed short job
loses less.

**Check that splitting is scientifically neutral before doing it** — confirm the
parts don't share state (seeded RNG constructed per part, no carry-over between
arms). If they do share state, say so and keep them together.

**Splitting a job must also split its output path.** Parts that used to run
sequentially inside one job now run *concurrently*. If they still write the same
results file, you have traded a walltime risk for a lost-update race, and the
loser is silent. Give each part its own output and merge at analysis time — which
is trivial when every record carries its own identifying fields.

## Adapt or abort — decide by what changes

When the cluster hands you less than you asked for, there are exactly two
legitimate responses. **The choice is not about how much less you got. It is
about whether the shortfall changes what you are measuring.**

- **Changes only cost** — time, batch size, parallel width, node count.
  **Adapt, and record the adaptation next to the result.** A run that is 40%
  slower measures the same thing. What makes this safe is the record; an
  unlogged adaptation becomes a result nobody can reproduce.
- **Changes what is measured** — a capability the experiment's *definition*
  depends on is missing, ignored, or silently substituted. **ABORT before the
  expensive resource is spent, and never run the reduced version under the
  original name.**

A crashed job costs an allocation. A job that quietly ran a different experiment
costs the allocation *and* poisons the analysis, and you may never find out.

**When unsure which case you are in, ask: if this run completes, will its output
file still deserve the name I am about to give it?** If not, that is the abort
case, however cheap the fix looks and however deep the queue is.

**Gate in this order — cheapest and most fatal first — all before any model
load, server start, or data staging:**

| Gate | Check | Why it must abort |
|---|---|---|
| **Semantic capability** | The feature the experiment's *meaning* depends on is actually active (e.g. constrained decoding really enabled, not silently ignored) | Highest stakes: the arm runs, completes, and measures something else entirely under its own name |
| **Parallel width vs devices** | Devices *allocated* == width requested (`nvidia-smi -L \| wc -l` vs your tensor/data-parallel setting) | Asking for width 2 with 1 device wastes the whole job |
| **Devices on one node** | `--nodes=1` was actually emitted | A total device count can be satisfied *across* nodes; most intra-job parallelism cannot span them |
| **Environment** | Import every module the entry point needs (`python -c "import numpy, sklearn, mypkg"`) | ~1 s here vs discovering it after a multi-minute model load |
| **Inputs present** | Caches/datasets exist and are readable | Offline modes cannot create a missing cache; the job dies late |
| **Walltime cap** | Requested time ≤ this cluster's maximum | Unsubmittable on capped clusters; needs checkpointing instead |
| **Output collisions** | This task's output paths are unique | See "Derive identifiers" |

**Every wait-for-a-service loop needs a timeout, and the timeout is a gate.**
Hardware fails in the middle, not politely at the start. A job whose server hung
during multi-GPU collective init — rank 0 logged its NCCL version, rank 1 never
arrived — was cut loose by a 10-minute health check and cost 10 minutes instead
of hanging out its full 8-hour allocation. Its node was drained by staff an hour
later with `Reason="Kill task failed"`, confirming the fault was hardware. An
unbounded `wait until healthy` converts a bad node into a full-allocation loss.

**A polling predicate that can match the poller itself never terminates.**
A timeout bounds a loop that is asking the right question slowly; it does not
save a loop asking a question that can never come true. The classic form is
`pgrep -f`, which matches against *full command lines* — including the command
line of the shell running the loop:

```sh
until ! pgrep -qf "myjob input.dat"; do sleep 5; done   # never exits:
                                                        # the loop matches itself
```

This ran for a day waiting on a process that had finished within the hour, at no
CPU cost and with no output, which is exactly why nobody noticed. Poll on
something that cannot describe the poller:

```sh
kill -0 "$PID" 2>/dev/null                 # a PID captured at launch
squeue -h -j "$JOBID" | grep -q .          # the scheduler's own record
test -e "$OUTDIR/DONE"                     # a sentinel the job writes
```

**Better still, do not poll for work whose completion is already reported to
you.** A backgrounded command that notifies on exit, or a Slurm dependency
(`--dependency=afterok:$JOBID`), removes the loop entirely. Reserve polling for
state nothing will tell you about, and give the interval a reason: an eight-minute
job does not need a five-second poll.

**One failed task in an otherwise healthy array is usually the node, not your
code.** Check whether the failure is isolated to one host before debugging
anything: `sacct -j <id> -X -o JobID,State,NodeList` next to
`scontrol show node <host> | grep -E 'State|Reason'`. Resubmit that index alone.

Two rules about the gates themselves:

- **Resolve all configuration before starting anything expensive.** Config
  handling is pure variable assignment; a config error should surface in one
  second, not after a 100 s model load on idle accelerators — times every task in
  the array.
- **Gate on what your entry points actually use.** A guard that imports a module
  nothing in the job needs adds a way to abort a job that would have succeeded.
  A gate that produces false aborts is worse than no gate.

## Results must survive a kill

**The flush unit must be strictly smaller than the smallest unit of work a
walltime can kill.** Anything a job finished must be on disk before it starts
the next thing.

The subtle version of this bug is a flush that *was* fine and stopped being
fine. Real case: results were flushed "after every row", where a row was one
twelfth of a job — correct. A later experiment ran **one row per job**, so the
identical code now wrote exactly once, at the very end. The job was killed at
~90% of its final unit and wrote **nothing at all** — including 4.8 GPU-hours of
a *completed* arm that existed only in process memory.

- Flush after every unit, not every batch of units.
- **Re-check granularity whenever the job's shape changes.** "Per row" is not a
  property of the code; it is a relationship between the code and the submission.
- Prefer append-only streams for large per-item output — they survive a kill for
  free. Whole-file rewrites do not.
- Ask directly: *if this dies at 90%, what is on disk?* If the answer is
  "nothing", fix that before submitting.

## Stage the campaign

**Never submit the full array first.** Submit one cheap task that exercises the
same machinery, and **write down the stage-2 trigger before stage 1 runs** —
afterwards you will rationalise whatever you see.

A trigger is a checklist with exact commands and a stated failure interpretation:

> Submit the remaining N only if: all smoke tasks `COMPLETED`; the log shows the
> derived config line; **and** both output files exist, each with exactly one
> record and the expected fields. *If only one file exists, the identifier is not
> reaching the code and the real array would clobber itself — fix that first.*

Design the smoke to exercise **the property you are unsure about**, at minimum
scale. Testing tag derivation needs *two* array tasks — one task cannot collide
with anything. Three generations is enough; a hundred proves nothing more.

**The point of staging is not that the predicted risk materialises.** A real
case: stage 1 was submitted to de-risk one specific thing, that thing turned out
fine, and stage 1 paid for itself anyway by exposing an unrelated flaw that would
have zeroed ~190 GPU-hours across every task in the array.

### Stage 1 validates the pipeline. It is not a preview of the result.

Do not read a scientific direction off the staged unit. Not as a hint, not as
"early evidence", not hedged.

Real case: a 12-cell campaign was staged on one cell. That cell produced a clean,
striking number, which was written up the same night as evidence against the
campaign's registered hypothesis — explicitly labelled "one cell, do not
generalise". The full campaign reversed the direction outright.

**The bias is structural, not merely small-n.** You stage on the cheapest,
fastest unit, because that is what makes a smoke test cheap — and cheapest is
systematically the least representative. In that case the staged cell was the
only one of twelve that ever reached the outcome being measured; every other cell
failed to reach it at any budget. Sampling the easiest unit and reading its
result is not a small sample of the campaign, it is a sample of the tail.

- Report stage 1 as **"the pipeline works"**, never as "early results suggest".
- Hedging does not license the inference. "One cell, do not generalise" attached
  to a directional claim is still a directional claim.
- If you catch yourself describing a stage-1 number as a *finding* rather than as
  a *check*, that is the tell.

## Derive identifiers, never hand-write them

**If N concurrent tasks each need a unique output path, compute it from the
array index.** Hand-writing more than a couple of tags is how a typo silently
destroys a result that took hours — undetectable downstream, because the file
exists and looks fine.

```bash
# Map SLURM_ARRAY_TASK_ID -> one cell + a unique tag; abort on out-of-range.
if ! ASSIGN="$(python3 grid_task.py --index "$SLURM_ARRAY_TASK_ID" --prefix "$PREFIX")"; then
  echo "ABORT: refused array index ${SLURM_ARRAY_TASK_ID}" >&2; exit 1
fi
eval "$ASSIGN"
echo "[grid] task ${SLURM_ARRAY_TASK_ID} -> ${TAG}"     # makes the mapping auditable in the log
```

- **Out-of-range must raise, never wrap.** Modular arithmetic turns an oversized
  `--array` back onto cell 0's tag — reintroducing exactly the collision the
  derivation exists to prevent.
- **`eval "$(cmd)"` discards `cmd`'s exit status.** Capture into a variable and
  test it, or a refused index yields an empty `eval`, leaves the variables at
  their unnarrowed defaults, and runs the *whole grid* under one tag.
- **Echo the resolved mapping**, so a log can be traced back to its task.
- Put the index arithmetic in a tested function, not inline in the batch script.

## Verify tracked state; do not trust your notes

**Status notes record what was *submitted*, and nobody goes back when it lands.**
Re-verify against the cluster at the start of every session before acting on
anything written down.

Observed repeatedly in one project: an array marked `PENDING` in the status file
had actually completed three sessions earlier — while later sessions were
already analysing its results. A deferred-defects list was twice wrong about its
own contents: one entry had been fixed long before, another described a defect
that never existed.

```bash
sacct -X -S <YYYY-MM-DD> -o JobID%16,JobName%20,State,Elapsed,ExitCode
sacct -j <arrayid> -X -n -o State | sort | uniq -c    # array state histogram
```

Then confirm the *artifacts*, not just the exit code: correct record count,
expected fields, the metric you think you measured. `COMPLETED` means the script
exited 0, not that it did what you meant.

## Common mistakes

| Mistake | Consequence |
|---|---|
| Anything CPU-heavy on a login node | Killed by staff; `salloc` was available in seconds |
| Budgeting walltime from a smaller model or shorter run | Off by 1-2 orders of magnitude; every task dies |
| Budgeting from a rate measured on a different cluster | Same code, same config, 2.6x slower on the new machine; CPU-bound work transfers worst |
| Treating two agreeing measurements as confirmation | Two similar machines agreeing predicts nothing about a third; it is one data point wearing two hats |
| Reading a scientific direction off the staged unit | You staged on the cheapest unit, which is the least representative one; the full campaign can and does reverse it |
| Calibrating on one unit when units differ in cost | The projection is right for that unit and 2-3x wrong for another; the slow ones die at ~75% and write nothing |
| Ignoring variance *within* a stratum | One seed finishes, its sibling times out on the same dataset |
| Raising the walltime globally to protect one slow stratum | Every task queues worse, possibly in a scarcer partition, for a minority's benefit |
| `scontrol update TimeLimit=` past the partition cap | Accepted, but the partition is not re-routed; the job waits forever as ordinary `(Priority)` |
| An unbounded wait-for-service loop | A node that hangs mid-init costs the whole allocation instead of minutes |
| A `pgrep -f` poll whose pattern appears in the poller's own command line | The predicate is always true; the loop outlives the job it watches, silently and at zero CPU |
| Timing only the first few units | Per-unit cost commonly rises; mean underestimates |
| One job holding accelerators for a CPU-only part | Pays GPU-hours for CPU arithmetic, and forces an unfittable walltime |
| Flush unit == job unit | A kill at 99% writes nothing, including finished sub-units |
| Assuming a flush granularity still holds after reshaping jobs | The code didn't change; the relationship did |
| Running on when a *meaning-changing* capability is missing | Completes, publishes, measures the wrong thing under the right name |
| Adapting to a smaller allocation without recording it | Result is real but unreproducible; later readers assume the original config |
| Splitting a job without splitting its output path | Sequential writes become concurrent ones; a lost-update race with a silent loser |
| Gates placed after the model load | Failure costs the allocation it was meant to protect |
| Guarding on imports the job never uses | Aborts jobs that would have succeeded |
| Submitting the full array first | The whole budget rides on untested machinery |
| Writing the stage-2 trigger after seeing stage 1 | You will rationalise whatever happened |
| A one-task smoke for a collision property | One task cannot collide; use two |
| Hand-writing N unique output tags | One typo silently destroys hours, undetectably |
| `eval "$(cmd)"` for derived config | Exit status discarded; a refusal becomes a silent no-op |
| Trusting a status file's job states | Rows are written at submit time and never revisited |
| Treating `COMPLETED` as "the result is right" | Exit 0 says nothing about what was measured |

## Red flags — stop and check

- About to run a loop, a parse, or a plot over ssh → that is a login node
- About to set `--time` from a number you did not measure at this configuration
- About to apply one unit's measured cost to units you did not measure — name the
  most expensive one and justify it, or measure per stratum
- About to carry a per-unit rate from another cluster, or from your laptop, onto
  the machine you are submitting to → that is an estimate, not a calibration
- Two measurements agree and you are treating that as confirmation → ask what
  they have in common; if it is "both are not the machine I am about to use",
  they corroborate each other and nothing else
- Writing a `wait until ready` loop with no timeout
- Writing a `pgrep -f`/`ps | grep` poll whose pattern matches the polling shell
  itself, so the loop cannot terminate at all
- About to submit >2 tasks of untested machinery → smoke one first
- Cannot answer "if this dies at 90%, what is on disk?"
- About to hand-write a third unique output tag
- A required capability is unavailable and you are considering continuing anyway
  → ask whether the output would still deserve its name. If not, **abort; a
  wrong result is worse than no result**
- About to justify staying on a login node with a runtime you have not measured
  → the estimate that lets you stay is the one you are least entitled to trust
- About to describe a stage-1 number as a finding rather than as a check → it is
  the cheapest unit, not a small version of the campaign
- Writing "early results suggest" about anything less than the full grid
- About to report progress from a status file you have not re-verified this session
- About to call a job successful because it exited 0
