# Protocol S2: do rewritten descriptions make the process skills load?

Written 2026-11-23, before either description is changed. Chosen by the researcher after S1 (journal
`2026-11-23.md`).

## Question

In S1 the target skill loaded in 21 of 48 runs. using-drac-clusters loaded in 1 of 15, and collaborating-on-research
did not load on r5 (sync a fix before asking), which failed in all 6 runs. **Do descriptions that name the
situations each skill covers, rather than only its domain, make the skills load, and does loading change the
decisions?** The drac scenarios used a generic "clusterX", which its description, keyed on Alliance cluster
names, cannot match. A separate condition with real cluster names separates the description fix from that bench
artifact.

## The change (branch `process-triggers`, from main)

Only the `description:` lines of `collaborating-on-research` and `using-drac-clusters` change. Nothing else in
either skill changes, and running-cluster-experiments is untouched.

- collaborating-on-research adds the moments that need it: before acting on a running campaign (syncing a
  fix, requeuing or rerunning, changing what is measured), and before spending compute on a number an
  earlier session recorded.
- using-drac-clusters adds shared academic Slurm clusters in general (MFA logins, shared login nodes,
  /home /project /scratch quotas) and the symptoms it covers (an expired ControlMaster read as an outage,
  whether something may run on a login node, writes that hang).

Both descriptions are written from the skills' own sections, not from the scenario texts. They were written
after S1's results were seen, so the real-incident half of the bench is the one most at risk of fitting them;
the skill-blind half is reported separately.

## Material and arms

S1's 16 scenarios, cases, prompt, tools and judge, unchanged. **All arms run the same day:**

| arm | what it is | scenarios | runs |
|---|---|---|---|
| `new` | target skill with the rewritten description | 16 | 48 |
| `old` | target skill as in S1 (description as published) | 16 | 48 |
| `without` | no skill | 16 | 48 |
| `new-named`, `old-named` | the 5 drac scenarios with real cluster names (clusterX → Narval, clusterY → Rorqual, example.ca → alliancecan.ca) | 5 | 15 + 15 |

174 runs. Judged as in S1 (judge parse fix included), all arms together, arm hidden.

## Measures and criteria

- **Primary (load rate):** Skill invoked, `new` vs `old`, per skill and pooled.
- **Decisions:** pass rate per arm; r5 by itself; skill-blind half by itself.
- **Bench artifact:** load rate of `old-named` vs `old` on the drac scenarios.

Pre-registered rule: merge `process-triggers` if (1) pooled load rate new > old, with collaborating-on-research and
using-drac-clusters each higher, and (2) pass rate new ≥ old − 2 (of 48). Otherwise report, and the researcher
decides. No bar on new vs without (S1 showed the bare agent at ceiling on most scenarios).

## Cost

174 runs at ~$0.13 ≈ $23; judge ≈ $5.

## Amendment 1 (2026-11-23, variant built, before any run)

- Variant frozen at **fed1737** (branch `process-triggers`): only the two `description:` lines change
  (collaborating-on-research 653 characters, using-drac-clusters 737). Old = main f680345 (S1's text).
- Named drac copies r2n r4n r8n b4n b5n: `clusterX` → `narval`, `clusterY` → `rorqual`, `example.ca` →
  `alliancecan.ca` in every file and in the situation; rubrics unchanged. Material in `private/s2/` (the 16 S1
  scenarios linked, not copied).
- Launcher `private/s2/launch.sh`; scorer `private/s2/score_s2.py` (S1's prompt and helpers); judge with S1's
  first-object parse.
