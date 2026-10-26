# Skill evaluations: journal

With/without measurements of the research skills, SkillsBench-style: the same task run by the
bare agent, by the agent with the skill, and by the agent with a skill it wrote for itself,
each protocol committed before its first scored run. Last updated 2026-10-26. Dated session
entries (the reasoning behind each step) are in `journal/`, from 2026-10-23.

## State

| Skill | Protocol | Material | Result |
|---|---|---|---|
| verifying-bibliography | stage 1 (`verifying-bibliography/PROTOCOL.md`) | 4 bibs, famous papers | ceiling in every arm: memory suffices |
| verifying-bibliography | long-tail (`longtail/PROTOCOL.md`) | 6 bibs, 17 defects after a memory filter | skill 1.00, bare 0.98, self 0.94; **both earlier runs measured instructions only** (scripts could not run in the sandbox; dated notices in both RESULTS) |
| verifying-bibliography | C (`longtail/PROTOCOL-C.md`) | same 6 bibs, scripts working | ceiling in every arm (1.00, 0 FP): the cases no longer discriminate |
| verifying-bibliography | D (`hard/PROTOCOL-D.md`, amendment 1; `hard/RESULTS-D.md`) | 6 real bibliographies (3 long, 3 identifier-poor), 364 entries, 13 page shifts after the memory filter | planted recall skill 1.00, bare 1.00, self 0.52 (5 of 12 runs timed out; completed runs 1.00): **criterion not met, bare at ceiling**. Secondary: on 70 natural errors in the sources (adjudicated arm-blind) skill 0.86 vs bare 0.77 (18 vs 5), same false positives (0.027) |
| verifying-bibliography | D2-D4 (`hard/PROTOCOL-D2..D4.md`) | D's six cases, reduced SKILL.md vs the full skill's D results | D2 (71 lines): planted 22/26, fail; D3 (follow-up of title-only entries restored): 26/26 but $1.77/run, fail; **D4 (follow-up as one scripted Crossref/DBLP pass): 26/26, 11 FP, natural 0.88, $1.04/run, all criteria met; reduction merged** (tuned on the same cases) |
| verifying-bibliography | E (`fresh/PROTOCOL-E.md`, `fresh/RESULTS-E.md`) | 6 fresh bibliographies, no plants; 18 confirmed natural errors | reduced 0.83, full 0.89, bare 0.86 recall; FP 8 / 7 / 12 entries; cost $1.06 / $0.98 / $1.98. **Criterion 1 missed by one hit**; reduction kept (researcher, 2026-10-24); given-name check raised to MAJOR afterwards, unmeasured |
| verifying-proofs | P1 (`verifying-proofs/PROTOCOL-P1.md`, amendments 1-4; `RESULTS-P1.md`) | fresh math.OC/stat.ML papers, one planted single-step error; calibration 46 bare runs, test 4 dropped-hypothesis cases | bare caught inequality 8/8 and algebra 6/8 even tightened; test skill 8/8 = bare 8/8 (**criterion not met**), other flags 1.25 vs 1.63 per run, all 20 sampled were real slips of the original paper |
| verifying-proofs | P2 (`PROTOCOL-P2.md`, `RESULTS-P2.md`) | P1's 4 test cases, reduced SKILL.md (86 lines) | reduced 8/8, 1.12 other flags, $1.68/run vs full 8/8, 1.25, $1.89: **all criteria met; reduction merged** |
| verifying-proofs | probe L1 (`PROBE-L1.md`, `RESULTS-L1.md`) | the 2 dev hypothesis plants the bare agent missed | Lean 4 + Mathlib: one refutation certified (15 min), one original lemma certified (25 min); exposed a flawed P1 plant (correction in RESULTS-P1) |
| verifying-proofs | L2-L3 (`PROTOCOL-L2.md`, `PROTOCOL-L3.md`, `RESULTS-L2-stage1.md`, `RESULTS-L2-stage2.md`, `RESULTS-L3.md`) | 12 sampled real-paper findings; 3 documented-defect papers | Lean certifies 9/11 real findings, refutes the false one; optional step used 0/6, default 3/3 with 7/7 clean certificates (6 faithful) at +17% cost; **merged as default**. *Corrected 2026-10-26:* documented defects found 4/6 per arm in stage 2 and 2/3 in L3 (0801.4243's span hits were a typo, not the defect) |
| verifying-proofs | L4 (`PROTOCOL-L4.md`, `RESULTS-L4.md`) | L3's 3 papers + one long paper (2608.28582), branch `lean-hyp` (missing assumptions certifiable) | documented defect certified 1/3 (was 0/3), found 2/3; 7/7 certificates CLEAN, none unfaithful; $0.84/run (+12%); long paper 10 min, $3.30, 2 certificates; merge pending |
| surveying-literature | A (`surveying-literature/PROTOCOL-A.md`) | 20 test drafts, 6 citations removed each | key non-memory Recall@30: bare 0.40, skill 0.38, self 0.41, script alone 0.05. No gain |
| surveying-literature | dev loop (`PLAN.md`, `dev_diag.py`) | 10 dev drafts | script variants (`--seedset`, `--rank coupling`, `--angles`) noise only; script-first workflow no gain; **search-method workflow +17 points** on non-memory refs |
| surveying-literature | B (`PROTOCOL-B.md`) | same 20 test drafts | search-method skill 0.52 vs bare 0.34: **+18.1 (criterion met, McNemar p=0.07)**; without any discard +11.7 (p=0.04, below the 15-point bar) |
| surveying-literature | B2 (`PROTOCOL-B2.md`) | 20 new test drafts, id-only contamination rule | skill 0.26 vs bare 0.20: **+6.0, criterion not met** (McNemar 3 vs 0, p=0.25); B+B2 pooled (secondary) 0.40 vs 0.31, +9.1, 11 vs 1, p=0.006. Skill kept; estimate +6 to +9 at 2.6x cost |
| surveying-literature | step 0 (`IMPROVEMENT-PLAN.md`) | 10 dev drafts, 1 run per arm | v3.1 (branch `surveying-v31`, b1594da): cost 0.64 of v2, non-memory 2/23 vs 4/23; **both thresholds missed**; measured anyway in B3 |
| surveying-literature | B3 (`PROTOCOL-B3.md`, frozen 7a99a33, amendment 1) | 35 new drafts (pool extended to reach 22 non-memory key refs), strict key rule | v3.1 0.205 vs bare 0.159: **+4.6, primary not met** (McNemar 5 vs 3, p=0.73); v3.1 - v2 = -2.2 (met); cost 0.75 of v2 (bar 0.70, not met); both skills lose memory-reachable recall (bare 0.92 vs 0.83) |

Spend: about $600 API-equivalent over 2026-10-08..10, about $134 more for B2 on 2026-10-11, about $290 for B3 on 2026-10-14..15, about $45 for protocol D on 2026-10-22..23 and $49 for D2-D4 on 2026-10-23, about $50 for E and about $100 for P1 (46 calibration and 16 test runs) on 2026-10-24. Runs repeatedly hit the account's session
limit; see the usage ceilings below.

## Open questions

1. surveying-literature: four measurements put the gain over the bare agent on hard references
   between +4.6 (B3) and +18 (B); v3.1 is live for its cost (0.75 of v2). Open: both skill
   versions lose references the bare agent names from memory (B3: 0.83 against 0.92). v3.2
   (branch `surveying-v32`) asked for the memory list in prose and was not followed (2 of 10 dev
   runs); a structural fix (the lookup script requiring the list) would need the B3 test drafts to
   measure, since the dev drafts cannot see the gap (`IMPROVEMENT-PLAN.md`, step 0b).
2. verifying-bibliography: reduced to its script by protocols D-D4; protocol E on fresh
   bibliographies missed its recall criterion by one hit (0.83 vs 0.89 full, 0.86 bare). Kept.
   On real errors the skill's measurable gain is cost (half the bare agent's), not recall.
3. verifying-proofs: no gain over the bare agent (P1); reduced without loss (P2). Lean 4 +
   Mathlib certification is now the default for false-step findings: a reliable certifier (L2: 9/11
   real findings, no false certification), not a discoverer (L2 stage 2: 6/6 with or without),
   used every time as a default at +17% cost (L3). Open: certificates on the documented defects
   themselves, and the cost on long papers.

## Data

- Public in the repo: protocols, RESULTS, score summaries (`results/`), gold labels
  (`verifying-bibliography/gold.json`, `longtail/gold.json`, `surveying-literature/gold.json`),
  frozen self-written skills with sha256.
- Local only (gitignored `private/` folders): arXiv sources and disguised drafts with the build
  pipeline (`surveying-literature/private/make_drafts.sh`), memory probes, dev diagnoses, and
  every raw run with its full trace (`*/private/runs/*.jsonl.gz`). Re-score with `analyze.py` or
  `score.py` on those files.

## Running an evaluation (what actually works)

- `claude plugin eval <skill dir>` on a skill folder; cases as `case.yaml` with `execution.prompt`
  and `context.scaffold_script` (a file), run with `--scaffold --keep-temp`.
- The scaffold must copy inputs into the working directory, install a frozen `_shared` into
  `$HOME/.claude/skills/_shared`, and write the S2 key to `$HOME/.config/scholarly/s2_key`
  (secret-looking EVAL_ variables arrive empty).
- Bash has no network unless each host is granted:
  `--allow-tools "WebFetch(domain:api.crossref.org)" ...` (same grants for every arm).
- `EVAL_SCHOLARLY_DISABLE=openalex` in the parent environment passes through.
- Verify from the traces that the script ran; a passing run proves nothing.
- `_harness/extract.py` turns results into JSONL; `_harness/probe.py` runs no-tool memory probes;
  `_harness/run_until_clean.py` redoes cases lost to a usage limit; `_harness/usage_gate.py` gates
  batches on the account's utilisation; `_harness/gated_cases.example.sh` shows case-by-case gating.

## Usage ceilings

Evaluation must stay at or under 50% of the 5-hour window and 80% of the 7-day window. Read both
with `python3 _harness/usage_gate.py --read`; launch one case at a time behind
`usage_gate.py --five 0.40 --seven 0.75`; default to 2 runs per case, reuse baseline arms when the
setup is unchanged, use a cheaper model for development loops, and prefer overnight runs.
