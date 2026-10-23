# Protocol D3 results: reduced skill with the WEAK follow-up restored (2026-10-23)

Protocol: `PROTOCOL-D3.md` (33ac52e), committed before the first run. 12 runs of the reduced skill
at 4c17d70 on D's six cases, 11:13 to 14:23 (the gate paused the batch about two hours for the
5-hour window), $21.2 in model cost. No run failed, none timed out, none was discarded.

| # | Criterion | D3 | Bar | D2 | Full skill (D) |
|---|---|---|---|---|---|
| 1 | Planted recall | 26/26 | at least 25/26 | 22/26 | 26/26 |
| 2 | False positives after adjudication | 17 | at most 22 | 17 | 15 |
| 3 | Natural-error recall | 131/146 = 0.90 | at least 0.80 | 0.89 | 0.83 |
| 4 | Script ran | 12 of 12 | at least 11 | 12 | 12 |
| 5 | Mean cost per run | **$1.77** | at most $1.40 | $1.27 | $1.05 |

The natural pool is now 73 errors (one more found in D3: `tu2019autozoom` cites AAAI with year
2018; DBLP has AAAI 2019, pp. 742-749). Every arm's recall is recomputed on it; the bare agent's
is 0.74.

**Verdict: criterion 5 fails, so the reduction is not published.** The restored instruction fixed
what it was meant to fix (26/26), but at 1.7 times the full skill's cost.

## Why it costs more

The restored text says to look each `WEAK` entry up "(DBLP, Crossref, the proceedings page)".
D3 agents did so one web search at a time: 23 and 25 WebSearch calls in the two long2 runs
($3.57 each), 11 in each poor1 run. D's full-skill runs reached the same 26/26 with almost no web
searches (17 in 12 runs, 10 of them in one run): they queried Crossref and DBLP with `curl` from
Bash, which costs nothing per lookup. Run cost tracks the number of web searches (the cost model
in the eval journal: about $0.36 per run plus $0.11 per search).

So the full skill's version of this guidance, a description of what the script does and does not
compare, led to a cheap scripted follow-up; the imperative "look each one up" in the reduction
led to per-entry web searches.
