# Skill evaluations: journal

With/without measurements of the research skills, SkillsBench-style: the same task run by the
bare agent, by the agent with the skill, and by the agent with a skill it wrote for itself,
each protocol committed before its first scored run. Last updated 2026-10-11.

## State

| Skill | Protocol | Material | Result |
|---|---|---|---|
| verifying-bibliography | stage 1 (`verifying-bibliography/PROTOCOL.md`) | 4 bibs, famous papers | ceiling in every arm: memory suffices |
| verifying-bibliography | long-tail (`longtail/PROTOCOL.md`) | 6 bibs, 17 defects after a memory filter | skill 1.00, bare 0.98, self 0.94; **both earlier runs measured instructions only** (scripts could not run in the sandbox; dated notices in both RESULTS) |
| verifying-bibliography | C (`longtail/PROTOCOL-C.md`) | same 6 bibs, scripts working | ceiling in every arm (1.00, 0 FP): the cases no longer discriminate |
| surveying-literature | A (`surveying-literature/PROTOCOL-A.md`) | 20 test drafts, 6 citations removed each | key non-memory Recall@30: bare 0.40, skill 0.38, self 0.41, script alone 0.05. No gain |
| surveying-literature | dev loop (`PLAN.md`, `dev_diag.py`) | 10 dev drafts | script variants (`--seedset`, `--rank coupling`, `--angles`) noise only; script-first workflow no gain; **search-method workflow +17 points** on non-memory refs |
| surveying-literature | B (`PROTOCOL-B.md`) | same 20 test drafts | search-method skill 0.52 vs bare 0.34: **+18.1 (criterion met, McNemar p=0.07)**; without any discard +11.7 (p=0.04, below the 15-point bar) |

Spend: about $600 API-equivalent over 2026-10-08..10. Runs repeatedly hit the account's session
limit; see the usage ceilings below.

## Open questions

1. surveying-literature: does protocol B's gain survive without the contamination rule's help? The
   60%-of-title-words rule discarded more skill than bare runs. Needs more drafts or a narrower
   title rule written before running (cost: roughly 15-20% of the 7-day window).
2. verifying-bibliography: a discriminating benchmark needs errors not reachable through Crossref
   or the web (old proceedings, theses, non-English venues) or long bibliographies (60-150 entries).
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
