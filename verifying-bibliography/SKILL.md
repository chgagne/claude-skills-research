---
name: verifying-bibliography
description: Use when checking a .bib or reference list for incorrect or fabricated entries — wrong titles, invented co-authors, wrong DOI/volume/pages, preprints cited instead of the published venue, or references that do not exist. Triggers on "verify this bibliography", "check my references", "are these citations real", a refs.bib alongside a paper, or suspicion that a bibliography was LLM-generated.
---

# Verifying Bibliography

## Overview

**Resolve a stable identifier first, then compare the record back against the `.bib`.**
Everything else in this skill follows from that one inversion.

The obvious design — take the title in the `.bib`, search for it, fuzzy-match the authors —
cannot detect the single most important defect. A fabricated title that accurately describes
the right paper retrieves that paper and passes. Searching *by* the thing you are trying to
verify is circular.

Two measured examples, both cleared by a title-search tool and both caught by reverse lookup:

- `moritz2019draco` carried the title *"Draco: An Approach to Generating Visualizations with
  a Computational Design Process"*. Its DOI is correct and resolves to *"Formalizing
  Visualization Design Knowledge as Constraints: Actionable and Extensible Models in Draco"*.
- `wongsuphasawat2016voyager` carried DOI `10.1109/TVCG.2015.2467251`, which resolves to
  *"High-Quality Ultra-Compact Grid Layout of Grouped Networks"* — a different paper by six
  different authors.

## Run it

```sh
python3 ~/.claude/skills/verifying-bibliography/assets/run-bibcheck.py \
    refs.bib --bbl main.bbl --out review-assets/
```

Run it by absolute path from the paper directory. Stdlib only — no install, no venv,
no dependencies. (`python3 -m bibcheck` also works, but only from `<skill>/assets/`.)

- `--bbl main.bbl` restricts checking to entries actually cited (the `.bbl` is ground truth
  for "cited", because it reflects the built document rather than every `\cite` including
  commented-out ones)
- `--out DIR` writes `bibcheck-report.md` and `bibdiff.csv`
- Exit code `2` means source coverage was degraded — see *When a source is down*

Optional: `S2_API_KEY` in the environment, or `~/.config/scholarly/s2_key`. Semantic Scholar
sits last in the ladder; on two real bibliographies it changed nothing. Absent, it is
silently skipped and nothing breaks.

## The ladder

```
1. DOI            -> Crossref /works/{doi}      authoritative, reverse check
2. arXiv DOI      -> arXiv API                  10.48550/* is DataCite, absent from Crossref
3. arXiv id       -> arXiv API
4. ACL DOI        -> aclanthology.org via Crossref
5. no identifier  -> DBLP by title              the CS/ML spine
6. still nothing  -> OpenAlex, then Semantic Scholar
```

Once a **non-preprint** identifier resolves, the weak rungs are skipped — they cost four
requests to four free APIs for no new information. A **preprint** record is the exception:
an arXiv hit says nothing about whether the work was later published, so the search
continues (see *Prefer the venue of record*).

DBLP is queried before OpenAlex because it is near-complete for NeurIPS/ICLR/ICML/ACL
proceedings, which frequently carry no Crossref DOI at all.

## Report author findings as set differences, never as a score

A scalar author-match score is worse than useless — it looks like evidence while hiding the
finding. The Voyager entry above scored **0.83** while carrying two invented co-authors and
one dropped real one. This tool prints:

```
+Bach, Bill, +Dragicevic, Pierre        -Bill Howe
```

Unmissable. Apply the same discipline in prose: name the authors, do not summarise the
disagreement.

## Severity

| Level | Meaning |
|---|---|
| `CRITICAL` | Wrong title under a resolved identifier, an author in the `.bib` absent from the record, or a DOI that does not resolve. Treat as fabrication until shown otherwise. |
| `MAJOR` | Metadata disagrees with a record reached by a stable identifier — venue, year, volume, issue, pages. |
| `MINOR` | Name form, punctuation, a field the venue does not use, or a preprint cited where a published version exists. |
| `WEAK` | Matched by title search only. **Not verified.** A human must look. |
| `UNVERIFIED` | No source returned a record. **This is a finding, not a pass.** |
| `SKIP` | Non-paper entry (blog, web page, anonymous artifact). Check the URL by hand. |

**`WEAK` and `UNVERIFIED` are not clean bills of health.** They are the entries most likely
to be fabricated, because a fabricated reference is exactly the one no database can find.

## What is compared against what

Identity must be established before any field comparison means anything.

- **Volume, issue, pages, year** are compared *only* against a record reached by a stable
  identifier. A title-search hit may be a different edition, a reprint, or a review of the
  same work. DBLP matched a *SIAM Review* review of Strogatz's textbook against a *Physics
  Today* review of it; comparing their page numbers is meaningless.
- **Year** additionally requires a non-preprint record. Indexes routinely pair the published
  venue with the preprint year — Semantic Scholar reports *DMLR 2022* for a paper published
  in DMLR in 2024 — so a weak year cannot distinguish an error from the normal preprint gap.
- **A title mismatch against a title-search record stops all further comparison.** If the
  titles disagree, we never identified the work, and reporting its year or authors would
  describe a different paper.

## Prefer the venue of record

When a paper has both an official publication and a preprint, the entry must cite the
**published version**. The preprint may stay in the entry as a supplementary `url`/`eprint`;
it never replaces the venue.

The check fires only when the entry cites the preprint *instead of* a venue —
`journal = {arXiv preprint arXiv:1808.04819}`, or no venue at all. An entry that names its
venue **and** carries `eprint`/`archivePrefix` is the desired state and is never flagged.

The claim "a published version exists" is only made on an identifier-resolved record or a
DBLP record. OpenAlex title matches invent confident-looking venues — it offered *"Int. J.
Neural Syst."* for the InfoNCE preprint and *"Open MIND"* for an unrelated 2026 paper.

## When a source is down

Sources fail, and a silent failure changes the findings. Two consecutive runs once produced
8 findings and then 7, purely because DBLP dropped connections.

- Per-host throttles (arXiv 3.0s, DBLP 2.5s, Semantic Scholar 1.1s, others 1.0s), 3 retries
  with exponential backoff, `Retry-After` honoured on 429
- **A circuit breaker**: after 3 consecutive failures a host is dropped for the rest of the
  run. Retrying is right for one flaky request and catastrophic for a host that is down —
  when arXiv began answering 429, 3 attempts × 15s on *every* entry turned a 12-second run
  into a **6.5-hour** one. A 404 does not trip the breaker: it means the host is healthy and
  the record is simply absent.
- Hosts that fail after retries are counted, reported on stderr, and set **exit code 2**;
  hosts dropped by the breaker are named separately
- Responses are cached in `~/.cache/scholarly/`; definitive 404/410 are cached too, so an
  unresolvable DOI is not re-requested every run. Transient failures are never cached.

**If you see the degraded-coverage warning, re-run before trusting the report.** A warm
cache makes consecutive runs byte-identical.

## Limits

State these rather than implying completeness.

- **Bib-style defects are invisible.** A non-normalised `booktitle` ("The Fourteenth
  International Conference on Learning Representations") is a real defect no record
  comparison can see. It surfaces as `WEAK` at best.
- **Given-name checks compare first initials only.** `Hoggan, Eve` → `Hoggan, Eve E.` is
  missed. Full given-name comparison was tried and reintroduced false alarms on the far more
  common initials-only form (`Dupré, B.` for `Benoit Dupré`), which is a worse trade.
- **`SKIP` entries are unchecked**, not clean. Anonymous artifacts and blog posts need a
  human to open the URL.
- The tool verifies that a reference *exists and is described correctly*. It says nothing
  about whether the citation supports the claim attached to it — that is selective citation,
  and it is handled in `reviewing-paper-sources`.

## Measured results

Against two bibliographies whose ground truth was established by prior manual review:

| | Entries | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|---|
| VIS paper | 18 | 7 | **0** | 2 | 1.00 | 0.78 |
| ML paper | 57 | 3 | **0** | 2 | 1.00 | 0.60 |
| HaRC 0.2.0, same files | 75 | 4 | 9 | 9 | 0.31 | 0.31 |

Acceptance benchmark (`tests/test_acceptance.py`, 6 must-fire and 10 must-stay-silent keys):
**precision 1.00, recall 0.83**.

It also found a defect the manual pass had missed: `caetano2023trees`, an *uncited* entry
whose DOI resolves correctly but whose pages read 410–418 against the record's 411–419.
Uncited entries are unaudited — check the whole file.

HaRC missed both fabricated titles described above, and false-alarmed on correct ACL entries,
LaTeX-escaped names (`Dupr\'e`), DBLP disambiguation suffixes (`Elena Rossi 0001`),
preprint-vs-published years, and textbook editions. Every normalisation rule in
`normalize.py` exists because one of those false alarms was observed on real data. See
`reference/fabrication-signatures.md`.

Timing: a cold 57-entry run takes minutes; warm runs take **10–20 seconds**, and consecutive
warm runs are byte-identical.

## See also

- `reference/fabrication-signatures.md` — the LLM-generated bibliography signature, the
  BibTeX comment traps, and the `.bbl` cross-check
- `reviewing-paper-sources` — consumes this report, writes the audit table and
  `refs-corrected.bib`, and checks selective citation
