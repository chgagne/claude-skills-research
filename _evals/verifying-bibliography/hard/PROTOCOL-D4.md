# verifying-bibliography, protocol D4: WEAK follow-up as one scripted pass

Written 2026-10-23, after D3 and before any D4 run. Frozen by the commit that adds it.

## Question

D3 (`RESULTS-D3.md`) met every criterion but cost: the restored `WEAK` follow-up led agents to one
web search per entry ($1.77 per run against a $1.40 bar). Branch `bib-reduce-d` at 61ee681 rewords
it: check all `WEAK` entries in one Bash script against Crossref and a single batched DBLP SPARQL
query, and use a web search only for an entry neither source finds. Does the reduced skill now
meet all of D2's criteria?

## Design and criterion

As D2 and D3 in every respect: same six cases, 2 runs each, same installation (`_shared` at
bf62212), grants, model, limits and gate; same scoring and adjudication rules; new natural errors
added to the pool for every arm. The skill under test is 61ee681; the comparator is D's full skill.

Criteria, unchanged: planted recall at least 25/26; at most 22 false positives; natural recall at
least 0.80; script ran in at least 11 of 12 runs; mean cost at most $1.40.

## Caveat and stopping rule

This is the third revision tuned on the same six bibliographies. A pass licenses publishing the
reduction with that limit stated in the results; it is not evidence that the reduced skill
generalises better than the full one. If D4 fails any criterion, the iteration stops here: the
branch is not merged and the full skill stays published, unless a new protocol on fresh
bibliographies is written first.
