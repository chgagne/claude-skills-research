---
name: self-verifying-bibliography
description: Check a BibTeX bibliography against the real published record. Finds fabricated or non-existent references, wrong titles, author lists, DOIs, venues, volumes, pages and years, retracted papers, and arXiv/bioRxiv preprints that have since been published. Use it when asked to check, audit, validate, fact-check, clean up or "fix" a .bib file or reference list, before submitting a paper or thesis, or whenever citations were written or edited by an LLM.
---

# Self-verifying bibliography

You are checking whether each BibTeX entry describes a work that **really exists**, and whether its fields **match the version of record**. The most important rule:

> **Every claim or correction must come from a record fetched during this session**: an API response, a DOI landing page, DBLP, arXiv, the publisher or the proceedings site. Never "fix" a field from memory. A correction written from memory is just another possible hallucination. If you cannot find an authoritative record, say so. Do not guess.

Not finding an entry in the APIs does not prove it is fabricated. Finding a similar title does not prove the entry is correct. The script narrows down where to look. You make the final decision for each flagged entry, with evidence.

## Tools in this skill

- `scripts/bibverify.py` (Python 3, stdlib only). Run it with the path relative to this SKILL.md.
  - `check REFS.bib [--cited-in main.tex ...] [--keys k1,k2] [--out r.json] [--md r.md] [--workers 4]` checks every entry against Crossref, doi.org, arXiv, DBLP, OpenAlex, Semantic Scholar, bioRxiv and Open Library. It writes a JSON report and a Markdown report, and prints the Markdown.
  - `lookup --title "..." [--author Surname]` / `lookup --doi D` / `lookup --arxiv ID` shows what each source says about one work. Use it during manual triage.
  - `bibtex --doi D` / `--arxiv ID` / `--dblp KEY` prints the BibTeX provided by the registry. Use it as raw material for corrections, then adapt it to the file's style.
- `REFERENCE.md` lists manual lookup endpoints, venue-specific sources (NeurIPS, PMLR, OpenReview, ACL Anthology, CVF, IEEE, ACM, PubMed, books) and search query patterns. Read it when you triage `not_found`, `unverified` or `review` entries.

Responses are cached in `~/.cache/bibverify` (override with `BIBVERIFY_CACHE`). Re-running is cheap, and an interrupted run resumes quickly. Optional environment variables: `BIBVERIFY_MAILTO` (Crossref/OpenAlex polite pool; set it only if the user provides an address for this purpose), `S2_API_KEY`, `OPENALEX_API_KEY`.

## Workflow

### 1. Scope
- Find the bibliography files (`*.bib`). If there is a LaTeX project, find the main `.tex` files or the `.aux` files. Passing them with `--cited-in` restricts checking to keys that are actually cited, and it also reports keys that are cited but not defined.
- Back up before editing: `cp refs.bib refs.bib.bak`.

### 2. Automated pass
```bash
python3 <skill-dir>/scripts/bibverify.py check refs.bib --cited-in main.tex \
    --out bibcheck.json --md bibcheck.md 2> bibcheck.log
```
Throughput is about 3 to 6 seconds per entry, because the APIs are rate-limited. A run on 100 or more entries can exceed a 2-minute shell timeout. In that case, run it in the background (`nohup ... &`), or with a long timeout, and poll `bibcheck.log`. If the run gets killed, re-run the same command. Cached lookups are not repeated.

### 3. Triage every entry that is not `ok`
Read `bibcheck.md`. Use `bibcheck.json` for full details: `findings`, `matched` (evidence records), `near_misses`, `published_version` and `suggest` (record values). Handle each status as follows:

| status | meaning | what to do |
|---|---|---|
| `not_found` | No index has a matching work. Possible fabrication. | Do a manual search (step 4). Look at `near_misses` first: a near miss with the same authors usually means the title is garbled; one with the same title but other authors usually means the authors are wrong. |
| `bad_identifier` | `doi_not_found`: the DOI is not registered. `doi_mismatch`: the DOI resolves to a different paper. `arxiv_not_found`/`arxiv_mismatch`/`arxiv_id_malformed`: same problems for the arXiv id. | These are strong signs of fabrication. Find the real work by title and authors. If it exists, replace the identifier with the correct one. If it does not exist, treat the entry as fabricated. |
| `retracted` | The cited work was retracted or withdrawn. | Do not delete it. Tell the user, because citing a retracted paper may still be intentional. |
| `mismatch` | Title, authors, year, venue, volume or pages contradict the record. | Confirm against the record listed in `evidence`. Use the DOI or publisher page when they disagree with an index. Then fix the fields. |
| `preprint_published` | A preprint is cited, but a published version exists. | Verify that the published version is the same work (step 5). Then convert the entry. |
| `review` | Warnings only: `title_differs`, `author_spelling`, `year_mismatch` of ±1, `venue_mismatch`, `venue_unconfirmed`, `preprint_journal_ref`, `number_mismatch`, `last_page_mismatch`, `doi_unchecked`. | Decide each one. `venue_unconfirmed` (the paper exists only as a preprint, but the entry claims a venue) is a frequent hallucination pattern. Check the claimed venue's proceedings directly. |
| `unverified` | Type not covered by scholarly indexes, such as a website, software, thesis, report or standard. | Verify by hand: open the URL, a repository or a library catalogue. |
| `error` | Script exception. | Verify by hand. |

`info` findings are not problems. For example, `doi_available` means a DOI could be added, and `record_authors` shows the record's author list for comparison.

Codes worth knowing:
- `author_not_in_record`: an invented or wrong author.
- `author_missing`: a dropped author.
- `first_author`, `author_order`: wrong order of authors.
- `year_before_arxiv`: the year is earlier than the arXiv id allows.
- `title_mismatch`: similarity < 0.9.
- `venue_mismatch`: shown as an error when a journal article's venue clearly contradicts the DOI record.

### 4. Manual verification (for `not_found`, `unverified` and doubtful cases)
Work through this list until you have an authoritative hit or have exhausted it:
1. `bibverify.py lookup --title "<title>" --author <first surname>` shows every source's candidates with similarity scores.
2. Use WebSearch with the exact title in quotes, then with the title and the first author's surname. Also try `site:dblp.org`, `site:arxiv.org`, `site:scholar.archive.org`, `site:semanticscholar.org`, and the publisher's or proceedings' site (see REFERENCE.md).
3. Search by author: WebFetch the authors' DBLP page (`https://dblp.org/search?q=<name>`) or their homepage publication list. A real paper by real authors appears there. A fabricated one does not.
4. Search for the claimed venue: open the proceedings table of contents or the journal issue for the stated volume and year, and look for the paper.
5. For books, use Open Library, Google Books or WorldCat by title, author or ISBN.

A work **exists** only if an authoritative page (DOI landing page, publisher, proceedings, DBLP, arXiv, PubMed, library catalogue) shows a matching title **and** matching authors. Blog posts, citation-farm pages and other papers' reference lists are not proof, because fabricated references propagate.

Classify each problem entry as one of:
- **Fabricated**: no trace anywhere after a thorough search, or only the identifier is real and it belongs to another work.
- **Corrupted**: a real work with wrong fields.
- **Real but unindexed**: confirmed by an authoritative page outside the APIs.
- **Unresolved**: you could not decide. Say why.

### 5. Preprint → published version
Before converting, confirm that the candidate is **the same work**: same authors (allow for additions), and the same or evolved title. The script also accepts identifier links (the arXiv `doi` field, Semantic Scholar, bioRxiv "published" link, Crossref `is-preprint-of`), and those can legitimately carry a changed title. Be careful with:
- **Workshop versions.** A 4-page workshop paper with the same title is not the full paper. Prefer the main conference or journal version, and look for one if the script only found the workshop version.
- **Substantially different papers.** A different title and a different scope can mean a different paper. If so, leave the entry and report it.
- **The text relies on preprint-only content**, such as an appendix or a theorem number. Flag this to the user rather than silently switching.

Then convert the entry:
- Change the entry type (`@article` or `@inproceedings`).
- Set `journal`/`booktitle`, `year`, `volume`, `number`, `pages`, `publisher` and `doi` from the published record.
- Remove `journal = {arXiv preprint arXiv:...}`, `CoRR` and `abs/...` volumes.
- You may keep `eprint`/`archivePrefix` if the file already uses them consistently.
- Conferences without DOIs (NeurIPS, ICML/PMLR, ICLR) are fine without one. Use the proceedings page as the evidence.

### 6. Editing rules
- **Never change citation keys.** The `.tex` files depend on them.
- **Keep the file's conventions**: field order, indentation, `{}` vs `""`, brace protection of capitals and acronyms (`{BERT}`, `{B}ayesian`), journal abbreviation style, month macros, `and others` usage. Bring in the correct *values*, not a different *format*. Registry BibTeX from `bibtex --doi` is raw material; adapt it.
- Take every value from the record you verified:
  - Use the full author list in record order, with the record's spelling of names. Keep LaTeX accents, for example `M{\"u}ller`.
  - For journals, use the year of the volume or issue. For proceedings, use the conference year.
  - Copy pages exactly; an article number is fine where the venue uses article numbers.
- Do not add fields you have not verified. Do not "complete" missing pages, volumes or DOIs from memory.
- **Fabricated entries:** do not delete them silently, and do not swap in a "similar" real paper on your own initiative, because the citing sentence may make a claim that the substitute does not support. Report each one with the evidence of absence and the citation sites (`grep -n '<key>' *.tex`). If the user asked you to fix things, you may propose a verified real replacement and say clearly that it is a substitution that needs author approval.
- Edit with precise, minimal edits, one entry at a time. Then re-check the changed keys:
  `python3 <skill-dir>/scripts/bibverify.py check refs.bib --keys k1,k2,k3 --out recheck.json --md recheck.md`
  If the project compiles, confirm that it still does (`latexmk`/`bibtex` without errors).

### 7. Report to the user
Finish with a concise report:
1. **Summary counts**: checked, ok, corrected, converted from preprint, fabricated, unresolved.
2. **Fabricated / non-existent** entries: key, what was claimed, how you searched, where it is cited. Put these first, because they need the author's attention.
3. **Corrections made**, per key: field → old value → new value, plus the evidence URL or DOI.
4. **Preprints replaced** by published versions, with venue and DOI or URL.
5. **Needs the author's decision**: retracted works, substantive version differences, unresolved entries, and duplicates.

Be honest about coverage. If some lookups failed (rate limits, network) and you did not finish checking them manually, say which entries remain unverified.

## Known false positives and pitfalls
- **Title changes between arXiv and venue versions** are common. Rely on identifier links and authors, not the title alone.
- **Year by ±1**: online-first vs print issue, conference held vs proceedings published (LNCS, IEEE), or an arXiv v1 vs a later version. Pick the year of the version cited, following the journal or conference convention.
- **Crossref quirks**: `subtitle` is stored separately. Titles may contain JATS/MathML markup. Proceedings `container-title` values are long ("2016 IEEE Conference on Computer Vision and Pattern Recognition (CVPR)"). Article numbers can appear in place of pages. Large collaborations can list thousands of authors while the bib uses a consortium name.
- **DBLP** names carry homonym numbers ("Wei Liu 0001", which the script strips), venues are acronyms, and arXiv appears as `CoRR`.
- **Many venues have no DOI or pages**: NeurIPS, ICLR (OpenReview), PMLR, and many workshops. Missing pages are not an error.
- **Names**: transliterations, diacritics, hyphenated and compound surnames, East Asian name order, initials vs full names. `author_spelling` is a warning for this reason. Check before "correcting" a name.
- **Venue matching is heuristic** (abbreviations, aliases, acronyms). Treat `venue_mismatch` warnings as prompts to look, not verdicts.
- **Generic short titles** ("Deep learning", "Attention") can match the wrong work. Check authors and year.
- **Index errors exist.** When sources disagree, the DOI landing page or the publisher's PDF is authoritative, then DBLP for CS proceedings, then the others.
- **`@misc`/`@online`/software/datasets**: verify the URL resolves and the content matches. For software, check the repository or Zenodo DOI and the version. For standards and legal or government documents, check the issuing body's site.
- **Rate limits**: Semantic Scholar often returns HTTP 429 without a key, so results based only on it may be missing. A `doi_unchecked` or `arxiv_unchecked` warning means "network", not "bad".
