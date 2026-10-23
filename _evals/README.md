# Skill evaluations: journal

With/without measurements of the research skills, SkillsBench-style: the same task run by the
bare agent, by the agent with the skill, and by the agent with a skill it wrote for itself,
each protocol committed before its first scored run. Last updated 2026-10-23.

## State

| Skill | Protocol | Material | Result |
|---|---|---|---|
| verifying-bibliography | stage 1 (`verifying-bibliography/PROTOCOL.md`) | 4 bibs, famous papers | ceiling in every arm: memory suffices |
| verifying-bibliography | long-tail (`longtail/PROTOCOL.md`) | 6 bibs, 17 defects after a memory filter | skill 1.00, bare 0.98, self 0.94; **both earlier runs measured instructions only** (scripts could not run in the sandbox; dated notices in both RESULTS) |
| verifying-bibliography | C (`longtail/PROTOCOL-C.md`) | same 6 bibs, scripts working | ceiling in every arm (1.00, 0 FP): the cases no longer discriminate |
| verifying-bibliography | D (`hard/PROTOCOL-D.md`, amendment 1; `hard/RESULTS-D.md`) | 6 real bibliographies (3 long, 3 identifier-poor), 364 entries, 13 page shifts after the memory filter | planted recall skill 1.00, bare 1.00, self 0.52 (5 of 12 runs timed out; completed runs 1.00): **criterion not met, bare at ceiling**. Secondary: on 70 natural errors in the sources (adjudicated arm-blind) skill 0.86 vs bare 0.77 (18 vs 5), same false positives (0.027) |
| verifying-bibliography | D2-D4 (`hard/PROTOCOL-D2..D4.md`) | D's six cases, reduced SKILL.md vs the full skill's D results | D2 (71 lines): planted 22/26, fail; D3 (follow-up of title-only entries restored): 26/26 but $1.77/run, fail; **D4 (follow-up as one scripted Crossref/DBLP pass): 26/26, 11 FP, natural 0.88, $1.04/run, all criteria met; reduction merged** (tuned on the same cases) |
| surveying-literature | A (`surveying-literature/PROTOCOL-A.md`) | 20 test drafts, 6 citations removed each | key non-memory Recall@30: bare 0.40, skill 0.38, self 0.41, script alone 0.05. No gain |
| surveying-literature | dev loop (`PLAN.md`, `dev_diag.py`) | 10 dev drafts | script variants (`--seedset`, `--rank coupling`, `--angles`) noise only; script-first workflow no gain; **search-method workflow +17 points** on non-memory refs |
| surveying-literature | B (`PROTOCOL-B.md`) | same 20 test drafts | search-method skill 0.52 vs bare 0.34: **+18.1 (criterion met, McNemar p=0.07)**; without any discard +11.7 (p=0.04, below the 15-point bar) |
| surveying-literature | B2 (`PROTOCOL-B2.md`) | 20 new test drafts, id-only contamination rule | skill 0.26 vs bare 0.20: **+6.0, criterion not met** (McNemar 3 vs 0, p=0.25); B+B2 pooled (secondary) 0.40 vs 0.31, +9.1, 11 vs 1, p=0.006. Skill kept; estimate +6 to +9 at 2.6x cost |
| surveying-literature | step 0 (`IMPROVEMENT-PLAN.md`) | 10 dev drafts, 1 run per arm | v3.1 (branch `surveying-v31`, b1594da): cost 0.64 of v2, non-memory 2/23 vs 4/23; **both thresholds missed**; measured anyway in B3 |
| surveying-literature | B3 (`PROTOCOL-B3.md`, frozen 7a99a33, amendment 1) | 35 new drafts (pool extended to reach 22 non-memory key refs), strict key rule | v3.1 0.205 vs bare 0.159: **+4.6, primary not met** (McNemar 5 vs 3, p=0.73); v3.1 - v2 = -2.2 (met); cost 0.75 of v2 (bar 0.70, not met); both skills lose memory-reachable recall (bare 0.92 vs 0.83) |

Spend: about $600 API-equivalent over 2026-10-08..10, about $134 more for B2 on 2026-10-11, about $290 for B3 on 2026-10-14..15, about $45 for protocol D on 2026-10-22..23 and $49 for D2-D4 on 2026-10-23. Runs repeatedly hit the account's session
limit; see the usage ceilings below.

## Open questions

1. surveying-literature: four measurements put the gain over the bare agent on hard references
   between +4.6 (B3) and +18 (B); v3.1 is live for its cost (0.75 of v2). Open: both skill
   versions lose references the bare agent names from memory (B3: 0.83 against 0.92). v3.2
   (branch `surveying-v32`) asked for the memory list in prose and was not followed (2 of 10 dev
   runs); a structural fix (the lookup script requiring the list) would need the B3 test drafts to
   measure, since the dev drafts cannot see the gap (`IMPROVEMENT-PLAN.md`, step 0b).
2. verifying-bibliography: reduced to its script by protocols D-D4 (`hard/RESULTS-D4.md`); the
   reduction was revised twice on D's cases, so a check on fresh bibliographies is still open.
3. verifying-proofs: not evaluated; planted errors in proofs with deterministic grading is the
   natural design (`surveying-literature/PLAN.md` lists the other skills).

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
