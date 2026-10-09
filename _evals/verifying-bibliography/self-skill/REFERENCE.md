# Manual verification reference

Use this file while you triage entries that `bibverify.py` could not settle. All endpoints below work without an API key, through `curl -sL` in Bash or through WebFetch. Keep the request rate modest. Most of these services throttle aggressive clients.

## Identifier checks

| What | Request | Notes |
|---|---|---|
| Does a DOI exist? | `curl -s https://doi.org/api/handles/<DOI>` | `"responseCode":1` means it exists. `100` (HTTP 404) means it is not registered. |
| DOI metadata (any agency) | `curl -sLH "Accept: application/vnd.citationstyles.csl+json" https://doi.org/<DOI>` | Works for Crossref, DataCite (arXiv, Zenodo) and mEDRA. |
| DOI BibTeX | `curl -sLH "Accept: application/x-bibtex" https://doi.org/<DOI>` | Raw material for a corrected entry. |
| Crossref record | `https://api.crossref.org/works/<DOI>` | Look at `title`, `subtitle`, `author`, `container-title`, `volume`, `issue`, `page`, `article-number`, `issued`, `updated-by` (retractions), and `relation` (`is-preprint-of` / `has-preprint`). |
| Crossref search | `https://api.crossref.org/works?query.bibliographic=<title+author>&rows=5` | Fuzzy search. Always check the authors of the top hits. |
| arXiv record | `https://export.arxiv.org/api/query?id_list=<id>` | `<arxiv:doi>` and `<arxiv:journal_ref>` point to the published version when the authors added them. |
| arXiv abs page | `https://arxiv.org/abs/<id>` | Shows the version history (`[v1] date`), the comments ("Accepted at ..."), and the journal reference. |
| arXiv BibTeX | `https://arxiv.org/bibtex/<id>` | |
| Retraction status | `https://api.openalex.org/works/doi:<DOI>` → `is_retracted` | Also check the Crossref `updated-by` field and the publisher page. |

## Search by title or author

- **DBLP** (CS): `https://dblp.org/search/publ/api?q=<words>&format=json&h=10`. Author pages are at `https://dblp.org/search/author/api?q=<name>&format=json`, then `https://dblp.org/pid/<pid>.html`. BibTeX for a record: `https://dblp.org/rec/<key>.bib`. If a CS paper has no DBLP record, either at its venue or as CoRR, treat that as suspicious.
- **OpenAlex**: `https://api.openalex.org/works?filter=title.search:<words>&per-page=10`, or `?search=<words>`. Author works: `https://api.openalex.org/works?filter=author.id:<A...>`.
- **Semantic Scholar**: `https://api.semanticscholar.org/graph/v1/paper/search/match?query=<title>&fields=title,authors,year,venue,externalIds`. Lookup by id: `/graph/v1/paper/DOI:<doi>`, `/paper/ARXIV:<id>`, `/paper/PMID:<id>`.
- **PubMed** (biomedical): `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json&term=<title>[Title]`, then `esummary.fcgi?db=pubmed&retmode=json&id=<pmid>`.
- **Europe PMC**: `https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=TITLE:"<title>"&format=json` (also covers preprints).
- **bioRxiv / medRxiv**: `https://api.biorxiv.org/details/biorxiv/<DOI>`. The `published` field gives the journal DOI, or `NA`.
- **Books**: Open Library `https://openlibrary.org/search.json?title=<t>&author=<a>` and `https://openlibrary.org/isbn/<isbn>.json`. Google Books `https://www.googleapis.com/books/v1/volumes?q=intitle:<t>+inauthor:<a>` or `q=isbn:<isbn>`. WorldCat search pages.

## Web search patterns (WebSearch)

- `"<exact title>"`. A real paper almost always has several hits: publisher, DBLP, Scholar mirrors, the authors' pages.
- `"<exact title>" <first-author surname>`
- `<first author> <second author> <key topic words> <year>`. Use this when the title might be garbled.
- `site:dblp.org "<title words>"`, `site:arxiv.org "<title>"`, `site:openreview.net "<title>"`, `site:aclanthology.org "<title>"`, `site:proceedings.neurips.cc "<title>"`, `site:proceedings.mlr.press "<title>"`, `site:openaccess.thecvf.com "<title>"`, `site:ieeexplore.ieee.org`, `site:dl.acm.org`, `site:link.springer.com`, `site:sciencedirect.com`, `site:pubmed.ncbi.nlm.nih.gov`.
- Only hits in other papers' reference lists, citation-generator sites or "AI summary" pages are **not** evidence of existence.

## Venue-specific sources of truth

| Venue | Authoritative source | Notes |
|---|---|---|
| NeurIPS / NIPS | `https://proceedings.neurips.cc/paper_files/paper/<year>` (older: papers.nips.cc) | Booktitle "Advances in Neural Information Processing Systems", volume = edition (e.g. 33 for 2020). No DOI. Pages exist only in older years. Datasets & Benchmarks track is separate. |
| ICML, AISTATS, COLT, CoRL, UAI (recent), etc. | `https://proceedings.mlr.press/v<vol>/` | PMLR volume number + pages. Each paper page has a BibTeX link. |
| ICLR | OpenReview: `https://openreview.net/forum?id=<id>`; API `https://api2.openreview.net/notes?forum=<id>` (older years: `api.openreview.net`) | No DOI or pages. Check the decision: "Accept (poster/spotlight/oral)" vs "Reject". A rejected or withdrawn submission is **not** an ICLR paper. Cite it as a preprint. |
| ACL, EMNLP, NAACL, EACL, TACL, COLING, workshops | `https://aclanthology.org/<id>` (BibTeX: `https://aclanthology.org/<id>.bib`) | Check "Findings of ..." vs main conference, and workshop vs main conference. |
| CVPR, ICCV, WACV (+ workshops) | `https://openaccess.thecvf.com/` and IEEE Xplore | Workshop papers are listed separately from the main conference. |
| ECCV | Springer LNCS (DOI 10.1007/978-3-...) and ecva.net | Proceedings year = conference year. Volume = LNCS volume. |
| AAAI | `https://ojs.aaai.org/index.php/AAAI` | Has DOIs (10.1609/aaai.v<vol>i<issue>.<id>). |
| IJCAI | `https://www.ijcai.org/proceedings/<year>/` | DOIs 10.24963/ijcai.<year>/<n>. |
| IEEE journals and conferences | IEEE Xplore (DOI 10.1109/...) | Early-access articles get a volume and pages later. Re-check entries that say "early access". |
| ACM | ACM DL (DOI 10.1145/...) | Article numbers are used instead of pages for many venues. |
| JMLR | `https://jmlr.org/papers/v<vol>/` | Volume + article number or pages. No DOI. |
| TMLR | OpenReview | Year = acceptance year. |
| Nature / Science / Cell, etc. | DOI landing page | Distinguish the main journal from family journals (Nature vs Nature Communications vs Scientific Reports). |
| Theses | ProQuest, the university repository, the national library (e.g. DART-Europe, EThOS, HAL theses.fr, Library and Archives Canada) | |
| Standards / RFCs | ISO/IEEE standards pages, `https://www.rfc-editor.org/rfc/rfc<n>` | |
| Software / datasets | GitHub/GitLab releases, Zenodo DOIs (DataCite), PyPI | Check the version and year. |

## Common fabrication patterns

- Plausible title + real, well-known authors in the right field, but no record anywhere. Check the authors' DBLP or homepage lists.
- Real title with wrong authors, often the authors of a related famous paper.
- Real paper with a wrong venue or year, e.g. a NeurIPS claim for an arXiv-only paper, or a journal claim for a conference paper.
- A DOI that is well-formed but unregistered, or that is real but belongs to a different paper, often in the same journal (prefix and journal code right, suffix invented).
- Pages, volume and year that are internally inconsistent for the journal, e.g. a volume that was published in a different year.
- An arXiv id whose YYMM is later than the cited year, or a 5-digit suffix before 2015.
- A "survey" or "position paper" by famous authors that does not exist.
- Mixed-up proceedings: a correct paper attributed to the sister conference or to a workshop.
