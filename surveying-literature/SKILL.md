---
name: surveying-literature
description: Use when finding related work a draft may have missed, checking whether a contribution has already been published, or mapping what a research area looks like. Triggers on "what related work did we miss", "has this been done before", "is our contribution novel", "map this field", "survey the literature on X", or a paper draft whose related-work section looks thin.
---

# Surveying Literature

## Overview

**Gap sweep**: from a draft, find the work it should have cited. The gap sweep is a search
method run by you, with web search; a script for the citation graph and for field maps is
optional (`reference/running-the-script.md`).

What a draft misses is mostly recent, topically adjacent rather than linked to its citations,
and indexed late. Measured on held-out drafts: nearly every hard reference that was found came
from a query naming a specific method, system or author; queries made of general words plus a
year found almost nothing, and searches past the eighth found almost nothing. Web search is
also the whole cost of a sweep: each `WebSearch` is a model call of its own. So the work is
eight precise queries, written from what you know, run four at a time, and candidates
confirmed against free indexes rather than searched for again.

## The method

1. **Know the contribution.** Read `main.tex` and its section files. The method section names
   the technical ingredients, the experiments name the baselines and benchmarks, the
   related-work section shows what is already cited. Write the contribution in one sentence
   and list its three to five ingredients.

2. **List what you know, as candidates.** The closest prior work you can name: methods,
   systems, acronyms, the authors or groups you associate with this problem. Write each one
   now as a line of `candidates.txt` (the title as you recall it; author and year after it when
   the title is uncertain) and note why it is close. This file is the raw material for the
   queries and the first half of the answer: on held-out drafts, the agent with no skill, listing
   from memory, recovered 92% of the removed references it knew; this method, before this step
   wrote them down, recovered 83%, because the search hits had taken their places. A reference
   the draft does not cite is a candidate from this step on, whether or not a search later shows
   it.

3. **Write 8 queries.** Every query has one of these three shapes, and the set has at least two
   of each:

   | Shape | Example |
   |---|---|
   | A method, system or acronym you know + the problem | `NASWOT MeCo zero-cost proxy ensemble neural architecture search` |
   | An author or group you associate with the problem + the ingredient | `Sutton Whitley Howe mutation rates (1+1)-EA pseudo-boolean` |
   | A technical ingredient + the problem as the community names it | `determinantal point process client selection federated learning` |

   The specific name is what makes a query find something; the problem words keep it on topic.

4. **Run the eight queries, four `WebSearch` calls per message.** Read the titles and collect
   every plausible candidate as the result shows it. These eight searches are the paid part of
   a sweep: each web search is a model call of its own, about a tenth of a dollar.

5. **Confirm the candidates offline.** Append the search hits, one title per line, to
   `candidates.txt` after the step-2 lines, and run

   ```sh
   python3 ~/.claude/skills/surveying-literature/assets/lookup-titles.py candidates.txt
   ```

   It asks Crossref and arXiv, free, about three seconds per title, and prints one line per
   title: `FOUND` with the exact title, first author, year, venue and DOI or arXiv id, or
   `NOT FOUND`. Then check the draft's `.bib` for each `FOUND` title: a cited one is not a gap.

6. **Rank by closeness to the contribution**, most threatening first: same problem and same
   method family, then same problem with a different method, then shared ingredients. The
   ranked list is every uncited line of `candidates.txt`, the step-2 ones and the search hits
   together, in that one order; where it came from does not move an entry. `FOUND` candidates
   come first, each with the identifiers the lookup printed; `NOT FOUND` candidates come after
   them, marked unconfirmed, with the author and year you have.

A sweep is two search messages, one lookup call and the answer. The script's output, when you
ran it, is a list of additions you confirm like any other candidate.

## Field map

From a topic rather than a draft: `run-survey.py . --field-map "<topic>"` clusters the area
into lines of work and orders them chronologically. See `reference/running-the-script.md`.

## Measured result

Held-out benchmark on recent arXiv drafts with six real citations removed each, scoring
Recall@30 on removed key prior work the model could not name from memory. Protocol A
(2026-10-09, script-first version): 0.38 with the skill, 0.40 without. Protocol B (2026-10-10,
12-query search method, same 20 drafts): 0.52 against 0.34-0.40. Protocol B2 (2026-10-11,
20 new drafts): 0.26 against 0.20; over both sets 0.40 against 0.31, and the skill almost
never missed a reference the bare agent found. Estimate: +6 to +9 points on the references a
user is least likely to know, at 2.5 times the cost per run. Run cost was 0.36 $ plus 0.11 $
per web search (R² 0.99), and that version made 19 searches per run, half of them to confirm
candidates.

The method above (protocol B3, 2026-10-15, 35 new drafts) did not replicate the gain: 0.205
against 0.159 without the skill (+4.6 points, noise-sized), and 0.227 for the previous version.
It replaced that version for its cost, 0.75 of it per run ($1.72 against $2.29), not the 0.70 the
protocol asked. On those drafts both versions also lost references the bare agent names from
memory (0.83 against 0.92 of the key ones), and the bare agent had the best overall recall: the
search hits took the slots of references step 2 would have listed. The method above answers
that by making the step-2 list part of `candidates.txt` and of the ranked answer; that change
is not yet measured. Details: `_evals/surveying-literature/`.

## Limits

- **A gap sweep finds topically adjacent work. It cannot judge whether a paper actually
  threatens the claim.** That is the reviewer's job: "cite and distinguish, or narrow the
  claim", not "you were scooped".
- **Recall is bounded by what you can name.** On the held-out drafts, the references no run
  found were classics outside the model's memory and preprints a few weeks old. If the user
  knows the area, ask for the two or three names they would search; one named query beats
  four general ones.
- **Anonymous and non-indexed work is invisible.** Workshop papers and preprints outside
  arXiv are often in no index.

## See also

- `assets/lookup-titles.py`: confirms a list of titles against Crossref and arXiv (`--json` for records)
- `reference/reading-a-gap-report.md`: what each grade in the script's report obliges you to do
- `reference/running-the-script.md`: the citation-graph sweep, its engines, grading and failure modes
- `reviewing-paper-sources`: Phase 0 offers this skill as an optional module
- `comparing-papers`: consumes the shortlist
- `verifying-bibliography`: shares the retrieval layer in `_shared/scholarly`
