---
name: using-drac-clusters
description: Use when working on a Digital Research Alliance of Canada (DRAC, Alliance, formerly Compute Canada) HPC cluster such as Narval, Rorqual, Fir, TamIA, Killarney, Vulcan, Nibi or Trillium — including ssh to *.alliancecan.ca failing with "Permission denied (keyboard-interactive)", sinfo/sacctmgr reporting "command not found" over ssh, submitting or monitoring Slurm jobs (sbatch, squeue, sacct, job arrays, GPU allocations), choosing between clusters, staging data into /project or /scratch, or jobs stuck PENDING.
---

# Using DRAC Clusters

## Overview

DRAC clusters are shared, MFA-gated, quota-bound Slurm systems. Three properties
drive almost every mistake: **you cannot authenticate on your own**, **login
nodes are not for computing**, and **almost nothing is knowable without asking
the cluster** — accounts, partitions, GPU types and quotas differ per cluster.

**Core principle: discover, don't assume.** Every value below has a command that
prints the truth. Run it once per cluster and cache it in the project's notes.

**Scope: this skill is the mechanics** — authenticating, finding the right
account and gres string, respecting quotas, moving files. For the *methodology*
of an experiment campaign — cost models and walltime budgeting, how to shape
jobs and arrays, gating a script on the compute it actually got, keeping results
alive through a walltime kill, staged submission — use
`running-cluster-experiments`.

## The MFA gate — read this before anything else

**MFA is mandatory on DRAC and an agent cannot complete it.** Non-interactive ssh
works *only* by multiplexing over a ControlMaster socket the user already
authenticated. Before concluding the cluster is down:

```bash
ssh -O check <cluster>      # "Master running (pid=...)" = usable
```

With no live master, **every** command fails identically with
`Permission denied (keyboard-interactive)`. That is not a transient error, a
wrong key, or an outage. Retrying cannot fix it.

**Do NOT engineer around the MFA prompt.** It is technically possible — pointing
`SSH_ASKPASS` at a script that auto-selects the push option will get an agent
through, and a subagent did exactly that during this skill's own testing. Do not
do it. MFA exists to put a human decision in front of every new session; a script
that answers it converts the user's phone into a rubber stamp and reproduces the
shape of an MFA-fatigue attack, even when the intent is benign. The user then
approves a push they did not initiate and cannot attribute.

**The gate is a stop, not an obstacle.** Report the blocker and ask. If the user
later says "go ahead and automate the prompt", that is their call to make
explicitly — never yours to assume from a task that merely needs cluster access.

### Two legitimate ways to open the master

**A. The user opens it in a REAL terminal.** Always available, needs no setup. An
agent-run shell cannot do this, however it is invoked (Claude Code's `!` prefix,
a tool call, `nohup`, a background job): MFA needs an interactive TTY, and
without one ssh falls back to `SSH_ASKPASS` and fails like this —

```
Pseudo-terminal will not be allocated because stdin is not a terminal.
ssh_askpass: exec(/usr/X11R6/bin/ssh-askpass): No such file or directory
Permission denied (keyboard-interactive,hostbased)
```

So the ask is specific: *"open Terminal/iTerm and run `ssh <cluster>`, complete
the MFA prompt."* They may exit immediately afterwards — `ControlPersist` keeps
the master alive once it exists.

**B. A GUI askpass, if the user has installed one.** With `SSH_ASKPASS` pointing
at a real dialog program (e.g. `theseal/ssh-askpass` on macOS) and `DISPLAY` set,
an agent can start the connection and the *user* answers a dialog on screen. This
removes the context switch, not the human.

**The distinction that matters is not GUI-vs-terminal, it is who answers.** A
dialog program ASKS the human; a script that returns a canned answer REPLACES
them. The first is fine. The second is the prohibition above.

**With askpass available, ANNOUNCE BEFORE CONNECTING.** Say that a dialog is
about to appear and why, then connect. The point is attributability: if the user
can always trace a prompt to something they were just told about, an
*unannounced* dialog becomes a reliable signal to refuse. Silently summoning
prompts destroys that signal even though every individual prompt is answered by a
human.

Installation note, if asked: install the package but do **not** run
`brew services start`. That agent `launchctl setenv`s `SSH_ASKPASS` **and**
`SUDO_ASKPASS` globally for every GUI app, putting a dialog in front of `sudo -A`
— far beyond what ssh needs. Export `SSH_ASKPASS` from the shell profile instead.

A socket that worked an hour ago proves nothing about now; re-check before a
batch of commands rather than discovering it mid-transfer.

Per-cluster `~/.ssh/config` that makes this work:

```
Host narval narval.alliancecan.ca
  HostName narval.alliancecan.ca
  User <username>
  ControlMaster auto
  ControlPath ~/.ssh/sockets/%r@%h-%p.sock
  ControlPersist 8h
```

`mkdir -p ~/.ssh/sockets` first — if the directory is missing, multiplexing fails
silently and every command re-prompts for MFA. With no master, `ssh -O check`
prints `Control socket connect(...): No such file or directory`.

## Never compute on a login node

Login nodes are for editing, transfers and `sbatch`, and staff kill offenders.
Cheap queries (`squeue`, `sinfo`, `sacct`, `diskusage_report`, `ls`) are fine;
anything looping over data, training, or running for minutes is not. Use
`sbatch`, or `salloc` for interactive work:

```bash
salloc --account=<alloc>_cpu --cpus-per-task=4 --mem=8G --time=1:00:00
```

## Discover the cluster, don't assume it

| What | Command |
|---|---|
| Which cluster am I on | `echo $CC_CLUSTER` |
| **Accounts you may charge** | `sacctmgr -n show assoc user=$USER format=Account%30 \| sort -u` |
| Partitions and their time caps | `sinfo -h -o "%P %l" \| sort -u` |
| GPU models actually present | `sinfo -h -o "%G" \| sort -u` |
| Quotas (space **and file count**) | `diskusage_report` |
| Your fairshare / why you are queued | `sshare -U -u $USER -o Account,RawUsage,LevelFS` |
| Job efficiency after it finishes | `seff <jobid>` (absent on some clusters — fall back to `sacct -j <id> -o Elapsed,MaxRSS,TotalCPU`) |

### How much actually varies — six clusters, same day, same user

This is why the principle is "discover, don't assume". Every value below was read
off the cluster with the commands above; none is inferred from another cluster.

| | Narval | Rorqual | Fir | TamIA | Killarney | Vulcan |
|---|---|---|---|---|---|---|
| Account | `def-x_cpu`/`_gpu` | `def-x_cpu`/`_gpu` | `def-x_cpu`/`_gpu` | **`aip-x`**, no suffix | **`aip-x`**, no suffix | **`aip-x`**, no suffix |
| Max walltime | 7d (`b5`) | 7d (`b5`) | **28d (`b6`, CPU)**; 7d GPU | **24h (`b3`)** | 7d (`b5`) | 7d (`b5`) |
| GPU partitions | `bygpu`+`bynode` | `bygpu`+`bynode` | `bygpu`+`bynode` | **`bynode` only** | **`gpubase_<model>_bN`** | `bygpu`+`bynode` |
| CPU partitions | yes | yes | yes (+`cpularge`) | yes | **none — GPU-only** | yes |
| GPU gres | `gpu:a100`, MIG `a100_3g.20gb` | `gpu:h100`, MIG `nvidia_h100_…_3g.40gb` | `gpu:h100` ×4, same MIG names | `gpu:h100` ×4, `gpu:h200` ×8 | `gpu:h100` ×8, `gpu:l40s` ×4 | `gpu:l40s` ×4 **+ `shard:l40s:16`** |
| `/home` | 50 GB / 500K | 50 GB / 500K | 48 GiB / 500K | **25 GiB / 250K** | 50 GiB / 500K | 50 GiB / **105M files** |
| `/scratch` | 20 TB | 20 TB | 19 TiB | **2 TB** | **500 GiB** | 5 TiB / **11G files** |
| `$HOME` | `/home/<u>` | `/home/<u>` | `/home/<u>` | **`/home/<l>/<u>`** sharded | `/home/<u>` | `/home/<u>` |
| `seff` | yes | yes | yes | **absent** | absent | yes |
| Slurm in non-login shell | yes | yes | yes | yes | **NO — needs `bash -lc`** | yes |

Three of those cells contradict what a reasonable person would generalise from
the first three columns, and each is its own trap:

**Time buckets do not stop at `b5`.** General-purpose clusters may expose `_b6`
at **28 days** for CPU, and `preempt` partitions running to 122 days. Reading
"`b5` = the maximum" off one cluster under-uses another by 4x. Conversely an AI
cluster may stop at `b3`. **Always read `sinfo -h -o "%P %l"`.**

**Partitions are not always named `bygpu`/`bynode`.** At least one cluster names
them **by GPU model** — `gpubase_h100_b3`, `gpubase_l40s_b3` — so a script that
greps for `bygpu` finds nothing and a `--partition=gpubase_bynode_b3` copied
across is rejected outright. On such a cluster you select hardware by partition,
not only by `--gpus=`.

**Some clusters have no CPU partitions at all.** A GPU-only cluster will reject
CPU-only preprocessing, so the "run it in `salloc` instead of on the login node"
advice has nowhere to land there — stage that work on a different cluster.

**Fractional GPUs come in two unrelated flavours.** MIG slices appear in the gres
string as `_1g.` / `_3g.` variants; **`shard:`** is Slurm's *time-sharing* of a
whole GPU (e.g. `shard:l40s:16` = 4 shards per card). Requesting a shard gives
you a card shared with other jobs, not a partitioned one — fine for small
inference, wrong for a benchmark you intend to time.

**Inode quotas differ by four orders of magnitude** — 250K on one cluster against
105M on another, because they are not the same filesystem. A pipeline that is
fine on one will wedge a group's quota on another.

### Some clusters set up Slurm only in a LOGIN shell

On most clusters `ssh <cluster> 'sinfo'` just works. On at least one it does not,
and the failure is loud in a misleading way:

```
bash: line 1: sinfo: command not found
bash: line 2: sacctmgr: command not found
```

with `$CC_CLUSTER`, `$SCRATCH` and `$PROJECT` all **empty**. The cluster is
fine — the Slurm binaries and site environment come from the login profile, and
a non-interactive `ssh <host> 'cmd'` never sources it. Every diagnostic you would
reach for to check whether the cluster is healthy fails at once, which reads
exactly like a broken or half-provisioned account.

**Fix: force a login shell.**

```bash
ssh <cluster> 'bash -lc "sinfo -h -o \"%P %l\" | sort -u"'
```

**Never conclude an account is unprovisioned from `command not found`.** Retry
through `bash -lc` first, and note per cluster whether it is needed — it changes
how every scripted command against that host must be written, including the ones
inside your job-submission wrappers. An empty `$SCRATCH` is especially dangerous:
a path built as `"$SCRATCH/data"` silently becomes `/data`.

**Accounts often but NOT always carry a resource suffix** (`<alloc>_cpu`,
`<alloc>_gpu`). Where they do, requesting a GPU under `_cpu` fails and CPU work
charged to `_gpu` burns a scarcer allocation. Where they don't (AI clusters using
`aip-` allocations), one account covers both. Always run `sacctmgr`; never copy an
account string between projects *or clusters*.

**Never construct user paths — use `$HOME` and `$SCRATCH`.** Some clusters shard
both by first letter, and the constructed form does not merely differ, it does
not exist:

```
narval/rorqual   HOME=/home/$USER         SCRATCH=/scratch/$USER
tamia            HOME=/home/<u>/$USER      SCRATCH=/scratch/<u>/$USER

                 where <u> is the first letter of your username
```

`ls /scratch/$USER` on TamIA returns `No such file or directory`. (`$PROJECT` is
not set on any of them — get the project path from `diskusage_report` or `ls
/project/`.)

**GPU gres strings are NOT consistent across clusters — always read them from
`sinfo -h -o "%G"`.** Two clusters, same year, same generation of hardware:

```
narval    gpu:a100  gpu:a100_1g.5gb  gpu:a100_3g.20gb          # short MIG names
rorqual   gpu:h100  gpu:nvidia_h100_80gb_hbm3_1g.10gb          # fully-qualified
```

A `--gpus=` string copied from another cluster's job script fails, and MIG slices
(the `_1g.` / `_2g.` / `_3g.` variants) are fractional GPUs — request one by
accident and you get a sliver of a card. Ask for a whole GPU explicitly.

**Time buckets decide your queue.** Partitions are binned by walltime: `_b1` ≤3h,
`_b2` ≤12h, `_b3` ≤24h, `_b4` ≤3d, `_b5` ≤7d. Asking 13h instead of 12h moves you
to a scarcer partition and can cost days of waiting — **round `--time` down into a
bucket**.

**How FAR the buckets go is a hard cap that differs per cluster.** General-purpose
clusters run to `b5` (7 days); AI clusters may stop at `b3`, making **24h the
maximum job length** — a 48h job is not slow to schedule there, it is impossible,
and long work must checkpoint and requeue. Always check:

```bash
sinfo -h -o "%P %l" | sort -u        # the authoritative bucket list
```

## Filesystems: file COUNT is the quota that bites

| | Purpose | Backed up | Watch |
|---|---|---|---|
| `/home` | code, configs | yes | small (~50 GB), low file cap |
| `/project` | shared datasets, results | yes | **file-count quota, often ~500K** |
| `/scratch` | large, regenerable, in-flight | **no** | **purged** (commonly 60 days) |

Space is rarely the limit; **inodes are** — millions of small files wedge a
group's `/project` while it looks half empty. Put re-fetchable data and
high-file-count output on `/scratch`.

**Copying into `/project` must preserve group ownership:**

```bash
rsync -a --no-g --no-p --stats src/ <cluster>:/project/<group>/<user>/<proj>/src/
```

Without `--no-g --no-p`, rsync imposes local ownership and breaks the setgid
group inheritance `/project` relies on, locking out collaborators. This fails
silently — verify after every transfer:

```bash
ssh <cluster> "cd <projdir> && find . -type f ! -group <group> | wc -l"   # must print 0
```

Use `--stats`, not `--info=stats1`, for a summary that prints reliably.

## Submitting and monitoring

**Calibrate before submitting an array.** Run ONE task, read its elapsed time,
then set `--time` with headroom. A 200-task array on a guessed walltime either
wastes an allocation or dies at 99%.

```bash
squeue -u $USER -o '%.14i %.22j %.8T %.10M %.10l %R'   # %R = why it is PENDING
sacct -X -S <YYYY-MM-DD> -o JobID%16,JobName%22,State,Elapsed,ExitCode
sacct -j <id> -X -n -o State | sort | uniq -c          # array state histogram
```

`-X` gives one row per job instead of per job step.

**Never pipe a running job's output through `tail`, `head` or `grep`** — they
buffer, so the file stays empty and you lose all visibility into something you
already started. Redirect to a file and read the file.

**One failed task in an otherwise healthy array is usually a bad node.** Look for
hardware-flavoured errors (e.g. `CUDA driver version is insufficient for CUDA
runtime version`) before suspecting your code; resubmit that index alone with
`sbatch --array=<n> <script>`.

## Common mistakes

| Mistake | Consequence |
|---|---|
| Retrying ssh after `Permission denied (keyboard-interactive)` | Cannot succeed; the user must re-authenticate MFA |
| Asking the user to authenticate via an agent-run shell | No TTY, so `ssh_askpass` fails; it must be a real terminal |
| Assuming a working socket stays working | Commands fail mid-session; re-check with `ssh -O check` |
| Copying an account string between projects or clusters | Job rejected; the `_cpu`/`_gpu` suffix does not exist everywhere |
| Copying a `--gpus=` string between clusters | Rejected, or a MIG sliver instead of a whole GPU |
| Copying a `--partition=` string between clusters | Some name partitions by GPU model (`gpubase_h100_b3`), so `bygpu`/`bynode` do not exist there |
| Requesting `shard:` thinking it is a whole GPU | You get a time-shared card; timings are meaningless |
| Concluding an account is unprovisioned from `sinfo: command not found` | Slurm may only be on the PATH in a LOGIN shell — retry via `bash -lc` |
| Building a path from an empty `$SCRATCH` in a non-login shell | `"$SCRATCH/data"` silently becomes `/data` |
| Assuming `b5`/7d is the longest bucket anywhere | Some clusters expose `b6` at 28 days; you under-use them by 4x |
| Assuming every cluster has CPU partitions | GPU-only clusters reject CPU-only work outright |
| Assuming `--time=48:00:00` will just queue slowly | On a `b3`-capped cluster it is unsubmittable; checkpoint instead |
| Hardcoding `/home/$USER` | Wrong on clusters with sharded homes; use `$HOME` |
| `--time` just over a bucket boundary | Scarcer partition, far longer queue |
| `rsync` into `/project` without `--no-g --no-p` | Group ownership broken, collaborators locked out |
| Judging `/project` headroom by disk space | Hit the file-count quota with terabytes free |
| Leaving output on `/scratch` | Purged; not backed up anywhere |
| Submitting a large array on a guessed walltime | Whole array dies near completion |
| Piping a running job's log through `tail` | Buffered; zero visibility into a job you started |

## Red flags — stop and check

- About to script `SSH_ASKPASS`, or otherwise auto-answer an MFA prompt → **stop
  and ask.** Completing the task is not worth silently spending the user's
  second factor
- About to run anything longer than a few seconds over ssh → that is a login node
- About to say the cluster is down → run `ssh -O check` first
- About to say an account is unprovisioned because Slurm commands are missing → retry through `bash -lc`
- About to reuse a partition name, bucket ceiling or gres string from another cluster → read `sinfo` on THIS one
- About to submit >20 tasks without having timed one → calibrate
- About to report a job's progress from a buffered pipe → you are reading nothing
