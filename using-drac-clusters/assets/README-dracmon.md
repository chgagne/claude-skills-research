# dracmon

A terminal monitor for Slurm jobs across Alliance (DRAC) clusters. It is view-only: it
never submits, cancels or edits anything. A background collector polls each cluster over
an ssh connection you have already opened, stores the results locally, and a Textual
interface shows them: jobs, experiment cells, usage, storage, and cluster state.

Verified on: (pending live check)

## Install and first run

You need [`uv`](https://docs.astral.sh/uv/) and a working ssh alias per cluster (see
`SKILL.md` for the login and MFA setup). Textual 8.2.8 is pinned in the script header,
so `uv` fetches it on first run.

```sh
uv run --script <skill>/assets/dracmon.py            # same as: ... tui
uv run --script <skill>/assets/dracmon.py doctor     # check the setup
```

| Subcommand | What it does |
|---|---|
| `tui` (default) | Interactive monitor. Starts a collector if none is running. |
| `collect [--once] [--wait-lock]` | Poll the clusters. `--once` runs one cycle and exits. `--wait-lock` waits (checking every 30 s) while another poller, such as the TUI's, holds the lock, instead of exiting 1. |
| `service install [--force]` / `uninstall` / `status` | Run the collector in the background. |
| `doctor` | Read-only checks: `uv` on PATH, Python version, askpass availability, and for each configured host `ssh -G` (ControlMaster, ControlPath and its directory, ControlPersist), with the fix to apply. Edits nothing. |
| `capture <cluster>... --out DIR` | Save anonymised raw cluster output (see Contributing a capture). |

Tabs: Jobs, Cells, Usage, Storage, Clusters (keys `1` to `5`). `R` refreshes, `w` changes
the usage window, `/` filters, `?` shows help, `q` quits. Below 80 columns or 20 rows a
compact view is used.

## Configuration

Config: `${XDG_CONFIG_HOME:-~/.config}/dracmon/config.toml`. State (database, logs):
`${XDG_STATE_HOME:-~/.local/state}/dracmon/`. Without a config file, all eight known
clusters are used with the host alias equal to the cluster name. **List only the clusters
you use**: `doctor` flags configured hosts that have no ssh alias or socket.

```toml
idle_release = 7200      # seconds with no jobs before a cluster is released
ssh_timeout  = 60        # hard limit on one poll; the ssh process group is killed after it

[[cluster]]
name   = "narval"
host   = "narval"        # ssh alias; defaults to name
pinned = true            # keep polling even when idle

[[cluster]]
name = "rorqual"

[cadence]                # seconds between polls of each kind of data
queue      = 300
cells      = 300
accounting = 900
usage      = 3600
disk       = 3600
partitions = 3600

[[glob_campaign]]        # progress for a campaign that does not use the cells hook
campaign  = "my-sweep"
cluster   = "narval"
done_glob = "$SCRATCH/my-sweep/results/*.json"
total     = 120
```

`done_glob` may start with `$SCRATCH/`, `$HOME/` or `~/`, which are expanded on the
cluster; any other pattern is relative to `$HOME`. Nothing else in it is expanded or
evaluated, only matched as a glob.

Other keys: `cells_retention_days`, `retention_days`, `usage_retention_days`,
`status_page`. `released_check` is deprecated and ignored (still accepted, so older
configs load). Unknown keys are an error.

## Background collector

```sh
uv run --script <skill>/assets/dracmon.py service install
```

On macOS this writes a launchd agent `dracmon.collector`; on Linux a systemd user unit
`dracmon.service`. `install` refuses to overwrite a different existing file unless you pass
`--force`. The service runs `collect --wait-lock`: while a TUI is polling, it waits for
the lock rather than failing and restarting. Without the service, the TUI runs the
collector itself while it is open.

## Cells: progress inside a job

A cell is one unit of work (a seed, a configuration) inside a job. Jobs call a hook that
appends one line per event to `$SCRATCH/.dracmon/cells/<campaign>/<jobid>.log` on the
cluster. The collector reads these logs; the Cells tab shows done/total per campaign.
Logs are deleted on the cluster after 30 days.

Shell (`dracmon-cell` is POSIX sh):

```sh
export PATH=<skill>/assets:$PATH       # or call it by full path
dracmon-cell plan 12                   # once: how many cells this campaign has
dracmon-cell start "seed3"
python train.py --seed 3 && dracmon-cell done "seed3" || dracmon-cell fail "seed3" "train.py exited non-zero"
```

Python (3.6+, stdlib only):

```python
import dracmon_cell as dc
dc.handle_sigterm()           # optional: record scancel/walltime (SIGTERM) as fail
dc.plan(12)
with dc.cell("seed3"):        # start, then done; any exception is recorded as fail
    train(seed=3)
# or explicitly: dc.start(name), dc.done(name), dc.fail(name, reason)
```

`scancel` and the walltime send SIGTERM, which kills Python without an exception, so
without `handle_sigterm()` the cell stays "running" in the Cells tab. `handle_sigterm()`
turns SIGTERM into `SystemExit(143)`, so `cell()` records fail with reason `SIGTERM`; it
replaces any SIGTERM handler your code installed. The shell helper cannot see the
signal; in a bash job script, use a trap:

```sh
cell=seed3
trap 'dracmon-cell fail "$cell" SIGTERM; exit 143' TERM
dracmon-cell start "$cell"
python train.py --seed 3 && dracmon-cell done "$cell" || dracmon-cell fail "$cell" "train.py exited non-zero"
```

Rules:

- The campaign name is `$DRACMON_CAMPAIGN` if set, else the Slurm job name. **Never leave
  a generic job name** (`job`, `run`, `train`, `sbatch`) as the campaign: unrelated
  campaigns merge. Set a specific name in the script: `#SBATCH --job-name=<specific>`.
- For chunks that resubmit themselves, export one `DRACMON_CAMPAIGN` in the script so
  every chunk reports into the same campaign, whatever its job name.
- The hook never fails a job. Every error is swallowed and both commands exit 0. If
  `$SCRATCH` is unset, nothing is written.
- The glob fallback (`[[glob_campaign]]`) only counts files matching a pattern. It cannot
  read file contents, so it cannot tell a failed cell from a missing one.

## Cluster states

| State | Meaning |
|---|---|
| active | Socket is open and the cluster has jobs, an open campaign, is pinned, or was active within `idle_release`. Polled on the cadences above. |
| released | Idle for `idle_release` (2 h by default). No command at all is sent, so the ssh socket expires on its own. It is not polled again until you press `R` or Connect, or its socket disappears and comes back (you ran `ssh <cluster>`); then it gets a full poll and is active again. A job submitted through a still-open socket is not seen until then. |
| down | The last poll failed or the socket vanished. Last good data stays on screen with its age. It is never shown as an empty queue, and stays down until a poll succeeds. |
| disconnected | Never active and no live socket. |

On a fresh install, each cluster with a live socket gets one full poll, even if it has no
jobs, so its data shows at once; after that the rules above apply. A released cluster is
not polled again until `R`, Connect, or its socket coming back.

## Connecting, and the MFA guarantee

dracmon never prompts and never answers MFA. Every collector ssh uses `BatchMode=yes`,
`ControlMaster=no` and disabled askpass, so it can only reuse a socket you opened yourself.
Without one, a cluster that was active shows as down; one that was never active shows as
disconnected.

The one way to open a connection is Enter on a cluster in the Clusters tab. That first
shows a warning that a Duo push will follow, with Cancel as the default. On confirmation it
runs `ssh -fN`, either through an askpass dialog or in the terminal with the monitor
paused. You approve the push yourself.

Nothing is left running on a login node. A poll runs a short script whose commands are each
wrapped in `timeout 20`, and the script exits.

## Data notes

- Usage is fetched in windows of at most 7 days (some clusters reject `sacct` ranges of
  29 days or more, and group queries are slow) and backfilled to 28 days. The Usage tab
  shows 1, 7 and 28 days and marks a window "partial" until it is filled.
- The Status column in the Clusters tab comes from the status.alliancecan.ca HTML table,
  fetched every 15 minutes with User-Agent `dracmon`. If that page changes shape the column
  goes blank; nothing else depends on it.

## Limits

- View-only. No submit, cancel or hold.
- No GPU utilisation: Slurm does not report it, and nothing is run on compute nodes.
- The queue GPU column is per node, so multi-node jobs are undercounted.
- Times use each cluster's UTC offset at poll time, so they can be off by an hour around
  daylight-saving changes.
- Recorded output exists for Narval, Rorqual, Nibi, TamIA, Killarney and Vulcan. **Fir and
  Trillium are not yet tested against a capture.**
- The glob fallback cannot read file contents (see Cells).

## Contributing a capture

If you have access to Fir or Trillium (or any cluster whose output changes), a capture
lets the tests cover it. With the socket open:

```sh
uv run --script <skill>/assets/dracmon.py capture fir --out ./capture
```

Read the files it writes, check that no username, account, project path, hostname or job
name remains (the anonymiser is a first pass, not a guarantee), then open an issue or pull
request with the files attached.

## Tests

```sh
cd <skill>/assets && python3 -m unittest discover -s tests
uv run --with textual==8.2.8 python -m unittest discover -s tests -p 'test_tui*.py'
```
