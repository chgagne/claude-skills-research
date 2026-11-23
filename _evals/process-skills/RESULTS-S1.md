# Results S1: process skills on decision scenarios (first measurement)

2026-11-23. Protocol: `PROTOCOL-S1.md` (+ amendment 1). 16 scenarios (8 rebuilt from real incidents, 8 written
skill-blind), each with its target skill installed vs no skill, 3 runs per arm (96 runs, no contamination,
$0.09-0.22 per run). Judged by Sonnet against rubrics committed before any run (3 flips in 96, tie-broken). No
pass bar (researcher's choice).

## Verdict

> **Correction (2026-11-23, after S2).** The r3 effect described below as "the one large effect" (skill
> 3/3, bare 0/3) did not replicate at that size the same day in S2: old skill 1/3, new 2/3, bare 1/3. Pooled
> over both days: skill 6/9, bare 1/6. Still in the same direction, but at 3 runs per arm it is not the clear
> effect claimed here. The S1 numbers themselves are unchanged. See `RESULTS-S2.md`.


**Overall the skills barely change the decisions: 38/48 passes with the skill vs 35/48 without (+0.06; better on
3 scenarios, worse on 1, sign test p = 0.63).** The bare agent already makes the right call in most scenarios.
The one large effect is a lab-specific rule: told about 60 cells that timed out at 24 h, the agent with
running-cluster-experiments refuses a 72 h resubmit and adds checkpointed ≤24 h chunks (3/3); the bare
agent resubmits at 72 h (0/3). **The bigger finding is that the skills often do not load.** The skill was invoked
in 21 of 48 skill-arm runs. using-drac-clusters loaded in 1 of 15, so it was effectively not tested.

## Numbers

| | skill | without | diff | skill invoked |
|---|---|---|---|---|
| all 16 scenarios | 38/48 | 35/48 | +0.06 | 21/48 |
| real incidents (8) | 19/24 | 16/24 | +0.12 | |
| skill-blind (8) | 19/24 | 19/24 | 0.00 | |
| running-cluster-experiments (6) | **18/18** | 14/18 | +0.22 | 10/18 |
| using-drac-clusters (5) | 10/15 | 9/15 | +0.07 | **1/15** |
| collaborating-on-research (5) | 10/15 | 12/15 | −0.13 | 10/15 |

Per scenario (skill / without, of 3; invoked): r3 24 h timeouts **3/0** (3); b1 silent task failures 3/2 (1);
b4 job on a busy login node 3/2 (0); b8 end-of-session record **1/3** (3); everything else equal: r1 r2 r4 r6 r7 b2
b3 b6 b7 3/3 in both arms, r8 1/1, r5 0/0, b5 0/0.

## Reading by scenario

- **r3 (timeouts → 72 h): the skill's rule changes the decision.** The bare agent's plan is a 72 h resubmit, with
  checkpointing only as a fallback. With the skill it adds per-generation checkpointing and chains 24 h chunks. This
  rule is a convention of this lab (long walltimes get low priority), and the bare agent does not know it.
- **r5 (sync a fix that changes what the arms can be compared on): all 6 runs fail, both arms.** Every answer
  rsyncs the runner first and tells the researcher afterwards. This is the exact incident behind the worked
  example in collaborating-on-research, and the skill was **not invoked in any of the 3 runs**. The situation
  reads as a cluster task, not as "a long-running research collaboration", so the description does not fire.
  This is the costliest miss on the bench.
- **b8 (end-of-session record): skill arm worse, partly a rubric conflict.** All arms commit named files
  only. One skill run marked a running job "UNVERIFIED" rather than "still running", which follows the skill's
  own rule (verify tracked state, do not assert it from a note), but the rubric wanted "still running". Another
  left an item out.
- **b5 (cron poll after MFA expiry): both arms 0/3.** Every answer diagnoses the expired connection correctly
  and tells the researcher to reopen it. All leave the cron entry firing (guarded by `ssh -O check` or BatchMode),
  where the rubric wants it disabled. This is a strict rubric point, the same in both arms, and tells us nothing.
- **r8 (rsync stuck in D state): 1/3 in both arms.** Nearly every answer recognises the filesystem-side stall,
  and most check the status page. They fail on the rest of the rubric: they do not offer to wait or to stage to
  `$SCRATCH`, or they plan a retry from another node.
- **Ceiling everywhere else:** login-node processing, MFA socket expired, wrong project path, a STATUS headline
  contradicted by summary.json, a new driver missing a flag, resume from a checkpoint, an ablation that ran the
  wrong config, a metric switched to flatter a null result, a headline from a mismatched budget. The bare agent
  passes all of them 3/3.

## What this means for the three skills

1. **Triggering is the first problem.** A skill that does not load cannot help. using-drac-clusters triggers on
   cluster names (Narval, Rorqual, ...), and the bench used generic names, so its 1/15 is partly a bench
   artifact. collaborating-on-research did not load on the one scenario it most needed to (r5).
2. **Where they load, most of their content repeats what the bare agent already does.** The measurable value is
   in rules specific to this lab (24 h chunks) and in situations the bare agent gets wrong (r5, r8), not in
   general good practice.
3. **The real-incident half shows the larger effect** (+0.12 vs 0.00 on the skill-blind half). That is expected,
   since the skills were written from those incidents. It is also a bias, which is why the skill-blind half was
   built.

Spend: 96 runs ~$13, judge ~$3, scenario writing ~$2. A first attempt failed validation before any run (the cases
lacked a `graders/` folder). The judge's parser was fixed to read the first JSON object.
