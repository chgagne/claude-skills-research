---
name: verifying-bibliography
description: Use when checking a .bib or reference list for incorrect or fabricated entries — wrong titles, invented co-authors, wrong DOI/volume/pages, preprints cited instead of the published venue, or references that do not exist. Triggers on "verify this bibliography", "check my references", "are these citations real", a refs.bib alongside a paper, or suspicion that a bibliography was LLM-generated.
---

# Verifying Bibliography

**Run the script, then read its report.** `bibcheck` resolves each entry by a stable
identifier first (DOI, arXiv id, then DBLP by title) and compares the record back against the
`.bib`, so a fabricated title under a correct DOI is caught. It checks every entry, which a
manual pass over a long bibliography does not.

## Run it

```sh
python3 ~/.claude/skills/verifying-bibliography/assets/run-bibcheck.py \
    refs.bib --bbl main.bbl --out review-assets/
```

Run it by absolute path from the paper directory. Stdlib only, nothing to install.

- `--bbl main.bbl` restricts checking to entries actually cited. Leave it out to audit the
  whole file: uncited entries carry errors too.
- `--out DIR` writes `bibcheck-report.md` and `bibdiff.csv`.
- **Exit code 2 means a source was down and coverage was degraded. Re-run before trusting the
  report.** Responses are cached, so the second run is fast.

## Read the report

| Level | Meaning |
|---|---|
| `CRITICAL` | Wrong title under a resolved identifier, an author absent from the record, or a DOI that does not resolve. Treat as fabrication until shown otherwise. |
| `MAJOR` | Venue, year, volume, issue or pages disagree with a record reached by a stable identifier. |
| `MINOR` | Name form, punctuation, an unused field, or a preprint cited where a published version exists. |
| `WEAK` | Matched by title search only. **Not verified.** |
| `UNVERIFIED` | No source returned a record. **A finding, not a pass.** |
| `SKIP` | Non-paper entry (blog, web page, artifact). Check the URL by hand. |

- **The script compares venue, year, volume and pages only against a record reached by a DOI
  or arXiv id.** A `WEAK` entry was matched by title alone, so none of those fields was
  checked, and `bibdiff.csv` shows no record for it. List every `WEAK` key, look each one up
  (DBLP, Crossref, the proceedings page) and compare its pages, volume, venue and year
  yourself. Entries without a DOI are where wrong page ranges hide.
- `WEAK` and `UNVERIFIED` entries are also the ones most likely to be fabricated: an entry no
  database can find is never clean until a human has found it.
- Author findings are printed as set differences (`+Bach, Bill  -Bill Howe`). Report them
  the same way: name the authors, never a match score.
- A preprint is flagged only when it replaces a venue. An entry that names its venue and also
  carries an `eprint` is correct.
- Page ranges can differ legitimately between CVF open access and IEEE Xplore for CVPR and
  ICCV papers. Check the CVF page before reporting a page error on those.

## Limits

State these rather than implying completeness: venue-name style is invisible to the tool;
given names are compared by first initial only; `SKIP` entries are unchecked; DBLP covers
computer science, so a preprint published in another field's journal may not be found. The
tool checks that a reference exists and is described correctly, not that it supports the
claim it is cited for (that is `reviewing-paper-sources`).

## Measured

- Two hand-audited bibliographies (18 and 57 entries): precision 1.00, recall 0.78 and 0.60.
- The repository's with/without evaluations: on planted defects the bare
  agent with web tools matched the skill every time (protocols C and D, recall 1.00 in both
  arms). On 364 entries of six real bibliographies, the skill found more of their own errors,
  mostly published papers cited as preprints: 0.86 against 0.77, at the same false-positive
  rate. That systematic pass is what the skill adds.

## See also

- `reference/design-notes.md`: the lookup ladder, what is compared against what, source
  failures and the circuit breaker, and the false alarms each normalisation rule fixes
- `reference/fabrication-signatures.md`: the LLM-generated bibliography signature, BibTeX
  comment traps, the `.bbl` cross-check
- `reviewing-paper-sources`: consumes this report and checks selective citation
