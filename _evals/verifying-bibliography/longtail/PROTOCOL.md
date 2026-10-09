# verifying-bibliography: long-tail evaluation

Drafted 2026-10-09 after stage 1 (`../RESULTS.md`) hit ceiling in every arm. A new
protocol, not stage 2 of the first: the case set changes and a memory filter is added.
Frozen at the commit that adds `gold.json`, before any scored run.

## Question

On references the model cannot verify from memory, does `verifying-bibliography` let an
agent find substantive errors better than the same agent without it, and better than a
skill the agent wrote for itself?

## Material

**Source.** The reference lists of published papers by one research group in genetic
programming, evolutionary computation and applied ML. These are long-tail works: workshop
and small-venue papers, theses, non-ML journals. The source papers are published, so their
reference lists may be shown publicly. Unpublished drafts are never used.

**Composition.** 6 bibliographies of about 10 entries each, about 60 entries in all.
- About a quarter of the entries are works published in 2026, after the model's training
  cutoff, each with a DOI that resolved on the day the cases were built.
- About 20 entries carry one planted defect each, spread over the six labels: title under
  the right DOI (3), added or swapped author (3), DOI of another work (3), subtle metadata
  error such as one page digit, a year off by one or a wrong volume (5), arXiv preprint of
  a version published since (3), and a plausible nonexistent work in the field's style (3).
- The other entries are correct, copied from the version of record.

**Gold labels.** Each correct entry and each defect's source record is checked against the
DOI's Crossref record, or for works with no DOI against the publisher's or proceedings'
page, by hand. An entry that cannot be confirmed from a primary record is dropped, not
guessed. `gold.json` stays out of the public repository until the results are recorded,
because a run with WebSearch could otherwise find it.

## Memory filter (before any arm runs)

For each case, the bare model (`claude-opus-5-5`, no tools, no skill) gets the stage prompt
3 times and must answer from memory only. Any defect it flags in at least one of the 3
probes is too easy: it is replaced by a new defect of the same label on another entry, and
the new case is probed again. The filter is repeated until no defect is caught from memory,
at most three rounds; a defect still caught after that is dropped. Probe outputs are kept
in `probes/` and are not scored.

## Arms

Unchanged from stage 1, so the two stages compare:
- **without**: no skill, the baseline arm of the skill arm's `claude plugin eval` call.
- **skill**: `verifying-bibliography` at commit 2091ec8, unchanged since stage 1, including
  its DBLP rung. DBLP served an anti-bot page to scripts on 2026-10-08. Fixing that is a
  separate change, measured separately, so this stage measures the skill as it stands.
- **self**: the frozen `../self-skill/` (sha256 in `../self-skill.sha256`), not regenerated.

Same prompt as stage 1 (`../evals/*/prompt.md` template), same tools, `--model
claude-opus-5-5`, fresh HOME per run.

## Scale

6 cases x 3 runs x 3 arms = 54 runs.

## Scoring

`../score.py`, unchanged: recall over defective entries, false-positive rate over correct
entries, label accuracy secondary, a run with no parseable block scores 0 and counts as a
format failure. Contamination check: a trace mentioning `gold.json` or `_evals` is discarded.
Added, indicative only: an exact McNemar test pairing skill and without on each
(defect, run index) pair.

## Success criterion (same as stage 1)

The skill arm succeeds if **both** hold:
1. its pooled recall exceeds the without arm's and the self arm's by at least 20 points;
2. its pooled false-positive rate is not higher than either other arm's.

Cost and time per run are reported beside the scores. If criterion 1 holds against without
but not against self, the reading is that a skill helps and this one is not the reason.

## Stopping

No further stage follows automatically. A clear pass or failure is reported as such. If
the without arm still exceeds 0.8 recall, the memory filter failed and the result is
reported as uninformative, not as a failure of the skill.

## Steps to build the cases

1. List the group's published papers from the CV, and take reference lists from their
   arXiv sources or the Semantic Scholar references endpoint.
2. Sample about 45 cited works, favouring low citation counts, plus about 15 works published
   in 2026 in the same fields, from Crossref with a 2026 date filter.
3. Verify every record by hand against its primary source; drop what cannot be confirmed.
4. Plant the defects, shuffle each case with a fixed seed, write `gold.json`.
5. Run the memory filter; replace and re-probe as above.
6. Commit the protocol with the frozen cases, keep `gold.json` local, then run the arms.
