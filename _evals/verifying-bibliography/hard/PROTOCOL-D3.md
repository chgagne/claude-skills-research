# verifying-bibliography, protocol D3: the reduced skill with the WEAK follow-up restored

Written 2026-10-23, after D2 and before any D3 run. Frozen by the commit that adds it.

## Question

D2 (`RESULTS-D2.md`) failed one criterion: the reduced skill missed 4 of 26 planted page shifts,
in two runs that never looked up the `WEAK` entries. Branch `bib-reduce-d` at 4c17d70 restores
that instruction (venue, year, volume and pages are compared only on identifier-resolved records,
so every `WEAK` entry is checked by hand) and drops the eval-folder path from the Measured section.
Does the reduced skill now meet all of D2's criteria?

## Design and criterion

As D2 in every respect: same six cases, 2 runs each, same installation (`_shared` at bf62212),
grants, model, limits and gate; scored with `private/scored/prep.py` and `score.py`; new
non-planted flags adjudicated with the same rules and added to the natural pool for all arms.
The skill under test is 4c17d70; the comparator is D's full skill.

Criteria, unchanged from D2: planted recall at least 25/26; at most 22 false positives; natural
recall at least 0.80; script ran in at least 11 of 12 runs; mean cost at most $1.40.

## Caveat

The restored text was written after seeing D2 fail on these same cases. A pass shows that the
instruction does what it was restored for; it does not show that the reduced skill generalises to
other bibliographies better than the full one. If D3 passes, the reduction is merged and may be
published; if criterion 1 fails again, the full "What is compared against what" section goes back
verbatim and the reduction is reconsidered.
