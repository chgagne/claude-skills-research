---
name: self-surveying-literature
description: Audit a research paper draft (LaTeX sources + .bib) for related work it should cite but does not, above all close prior work that undermines its novelty claims. Searches Semantic Scholar, arXiv, DBLP and Crossref, follows citation graphs, verifies every hit, and produces a prioritized, evidence-backed report plus BibTeX. Use when asked to find missing references/citations, check related-work coverage, test a novelty claim against prior art, do a pre-submission literature check, or anticipate reviewer comments like "the authors overlook X". Not for writing a related-work section from scratch or for formatting a .bib.
---

# Self-surveying literature: what should this draft cite but doesn't?

Act as the best-read reviewer the paper will get. The deliverable is a short, verified, prioritized
list of missing papers. Each one comes with the reason a reviewer would raise it and where it belongs
in the draft. It is not a dump of search hits. Missing one paper that threatens the novelty claim
costs the authors more than ten marginal "could also cite" suggestions, so put recall effort into
finding close prior work and put precision effort into what you report.

## Non-negotiables

1. **No paper from memory.** Every reported paper must come from an API record retrieved in this
   session (S2, arXiv, DBLP, Crossref). Memory is welcome for deciding *what to look for*. If you
   think "Smith et al. did this around 2019", run `s2.py match "<title>"` or search for it, and use
   the retrieved metadata.
2. **Read before you claim.** Read the abstract of every paper you report. Before calling a paper a
   novelty threat, read its method section in the full text. A title alone is never enough.
3. **Make sure it is really missing.** The draft may already cite another version (arXiv vs.
   proceedings, journal extension, different title, odd bib key). The scripts dedupe by IDs and fuzzy
   titles. Before reporting, also grep the .bib for the first author's surname and the year.
4. **Respect the time frame.** Prior work means work available before the draft's cutoff. Report
   later or concurrent work separately and label it as such.
5. **Don't edit the user's .tex/.bib** unless asked. Write everything to the work directory.

## Setup

```bash
S=/absolute/path/to/self-surveying-literature/scripts   # this skill's scripts dir
W=./related-work-audit                                    # work dir (created on demand)
```
Scripts use only the Python 3 standard library. The S2 key is read from
`~/.config/scholarly/s2_key`. S2 calls are throttled to about 1/s and arXiv calls to 1 per 3 s, so
large expansions take minutes. Run long commands in the background or in sequence, not in parallel
(parallel runs would break the rate limit). Every discovery command with `--work $W` appends to
`$W/pool.jsonl` and logs queries to `$W/queries.tsv`. Each script has `--help`.

## Phase 1: Understand the draft (do not skip; search quality depends on it)

```bash
python3 $S/draft_extract.py path/to/draft_dir --work $W     # or path/to/main.tex
```
This prints a digest with the title, authors, abstract, cites per section, novelty sentences,
statements about prior work with no citation, and .bib stats. Per-section cleaned text, with
`[CITE:key]` markers, is in `$W/draft.json`. Read the abstract, introduction, related work, method
overview and experimental setup, using the .tex where needed. Then write `$W/profile.md`:

- **Problem and setting** in one sentence, in generic words.
- **Contributions C1..Cn.** For each: the claim, the *mechanism* (what is actually new, described
  without the paper's coined names), and how it is evaluated.
- **Novelty claims, quoted verbatim** ("first to…", "unlike prior work…", "no existing method…").
  These are the hypotheses you will try to falsify.
- **Vocabulary map.** The draft's terms, synonyms, older names for the same thing, and the names
  used by neighboring communities (e.g., ML / statistics / signal processing / control / OR / IR /
  databases / HCI, or the CV vs. NLP vs. speech versions of an idea). The most dangerous prior work
  usually uses different words.
- **Positioning.** The cited works the draft treats as closest, the baselines, the subareas the
  related-work section covers, and obvious adjacent subareas it does not mention.
- **Artifacts used:** datasets, benchmarks, metrics, base models, libraries, theorems. Each needs a
  citation to its origin. Check whether it has one.
- **Cutoff date.** Style hints like `neurips_2026` or `iclr2027_conference` imply a deadline. Ask the
  user if it is unclear and matters. Most venues treat work that appeared within about 2 months
  before the deadline as concurrent.
- **Authors** (often still in the source even when the PDF is anonymized). Their own prior work is
  a classic omission. In a double-blind submission it must be cited in the third person.

## Phase 2: Map the bibliography to Semantic Scholar

```bash
python3 $S/s2.py resolve-bib --work $W
```
This writes `$W/cited.jsonl` (bib key, S2 paperId and metadata), resolving by DOI, then arXiv id,
then title match. It lists weak or unresolved entries and cited preprints that have since been
published. If an important cited paper is unresolved, find it (`s2.py match`, `s2.py search`) and
fix it with `--set KEY=PAPERID`, because seeds and dedup depend on this mapping.

## Phase 3: Generate candidates through several independent channels

No single channel is enough. Keyword search misses papers that use different vocabulary, citation
graphs miss papers from disconnected communities, and recommendations drift. Use all of them.

**3a. Keyword search, roughly 20–40 queries.**
```bash
python3 $S/s2.py search entropy minimization test-time adaptation --work $W
python3 $S/s2.py search '"test-time adaptation" + (entropy | "batch norm")' --bulk --sort citationCount:desc --work $W
python3 $S/sources.py arxiv 'abs:"test-time adaptation" AND abs:entropy' --work $W
python3 $S/sources.py arxiv test-time adaptation entropy --sort submittedDate --work $W   # recent
python3 $S/sources.py dblp test time adaptation entropy --work $W
python3 $S/sources.py crossref <query> --work $W        # journals/fields DBLP doesn't cover
```
- Use 2–6 content words per query. S2 relevance search is lexical, so full sentences do worse.
- For each contribution, search: mechanism + task; the mechanism's *generic* name + setting; task +
  the claimed property; each synonym and older name from the vocabulary map; and the neighboring
  community's phrasing.
- **Turn each novelty claim into a query.** "First to apply X to Y" means searching `X Y`, `X` +
  synonyms of `Y`, and `Y` + the generic description of `X`.
- Search what the method *does*, not only what it is called, e.g. "reweighting samples by
  gradient agreement" rather than the paper's acronym.
- Use `--year` to focus. Use `--bulk` with quoted phrases and `+ | -` operators for precise
  phrase queries.
- Run the 5–10 most important queries on arXiv (preprints and very recent work) and DBLP (CS
  venues, title-based) as well. Use Crossref when the topic reaches outside CS.
- Glance at the first ~15 printed hits after each query and adapt. When unfamiliar terms appear in
  relevant hits, add them to the vocabulary map and search for them.

**3b. Citation graph.** Pick 5–15 *anchors*: the cited works the draft positions itself against
(closest methods and baselines), not generic foundations.
```bash
python3 $S/s2.py cites --keys key1,key2,key3 --work $W   # newer work building on the anchors
python3 $S/s2.py refs  --keys key1,key2,key3 --work $W   # what the anchors build on
python3 $S/s2.py refs  --all-cited --work $W             # cheap co-citation counts across the whole bib
```
Forward citations of anchors (`cites`) are usually the richest source of close prior work. A paper
that cites several anchors is working on the same thing. `cites` skips seeds with more than 3000
citations because they are too generic. Override with `--force` only for a moderately cited anchor.

**3c. Recommendations.** `python3 $S/s2.py recommend --keys key1,key2,key3 --work $W`. Repeat
later with the closest *found* papers as positives (`recommend PAPERID ...`).

**3d. People.** For draft authors and for the first and last authors of the 2–3 closest works:
```bash
python3 $S/s2.py author-search "First Last"          # pick the id whose papers match the topic
python3 $S/s2.py author-papers AUTHORID --label "First Last" --work $W
```
S2 often splits or merges author profiles. Check against a paper you know they wrote.

**3e. Web.** WebSearch catches what APIs miss: workshop papers, OpenReview submissions, papers known
under a nickname, and blog posts that point to papers. Try the core idea in plain words, plus
`site:openreview.net` and `site:arxiv.org` variants. Add each paper you find through the API so it
becomes a verified record: `python3 $S/s2.py match "Exact Title" --work $W --tag web`.

## Phase 4: Rank the pool

```bash
python3 $S/pool.py rank --work $W --after 2026-05-15      # cutoff date if known
python3 $S/pool.py coupling --work $W --top 200            # ~200 S2 calls; re-ranks at the end
python3 $S/pool.py show --work $W --top 40                 # then --start 40, --start 80, ...
```
`rank` merges versions, removes papers the draft already cites, and flags `in-bib-uncited` entries
(in the .bib but never `\cite`d: easy wins to point out), the draft itself, and post-cutoff papers.
It prints a **recall proxy**: the share of the draft's own citations that your searches and
recommendations re-found. If it is well below about 50% of the topical citations, your queries are
too narrow or use the wrong vocabulary. Go back to 3a.

The score only orders your reading; the verdict is yours. The strongest single signal of a close
competitor is **bibliographic coupling** (`cpl9/40`: 9 of the candidate's 40 references are also
cited by the draft), especially combined with `cites≥2` (it cites several anchors) or high `sim`.
Review those regardless of rank: `pool.py show --work $W --min-sim 0.25 --top 100` and scan
`$W/shortlist.md` for high `cpl`/`cites` values.

## Phase 5: Triage by reading

Read the candidates in pages: at least the top 100–150, plus every high-coupling or high-similarity
paper. For promising ones without a usable abstract, run `python3 $S/s2.py paper ID` (abstract,
TLDR, open-access PDF). Assign each plausible paper one label and log it in `$W/triage.md` as
`id | label | one-line reason`, including rejections, so later rounds don't re-read them:

| Label | Meaning | Reviewer reaction if missing |
|---|---|---|
| **THREAT** | Same problem and same key mechanism, or achieves something the draft claims as "first", before the cutoff | "Not novel given [X]" (can sink the paper) |
| **DIRECT** | Same problem with a different method, or the same mechanism in a close setting. Often should be a baseline | "Missing comparison/discussion of [X]" |
| **ORIGIN** | Original source of a technique, dataset, metric or result the draft uses or re-derives, including when the draft cites only a later popularizer | "This idea goes back to [X]" |
| **XDOMAIN** | Same idea under another name in another community | "This is known as … in [field]" |
| **SELF** | Authors' own relevant prior work | Desk-reject risk if hidden; otherwise "how does this differ from your [X]?" |
| **SURVEY** | Recent survey or benchmark of the subarea (report at most 1–2) | Minor |
| reject | Topical, but a knowledgeable reviewer would not expect it | — |

The **reviewer test**: would an expert reviewer in this subarea write "the authors should cite and
discuss X"? Citation count is not the test. A 3-citation paper with the same mechanism outranks a
famous loosely related one. Be strict about "same mechanism". Two methods that share a buzzword
are not overlapping, while two methods with different names but the same objective or algorithm are.

## Phase 6: Snowball until saturation

Take the accepted THREAT/DIRECT/XDOMAIN papers as new seeds:
```bash
python3 $S/s2.py cites PAPERID1 PAPERID2 --work $W
python3 $S/s2.py refs  PAPERID1 PAPERID2 --work $W
python3 $S/s2.py recommend PAPERID1 PAPERID2 --tag round2 --work $W
```
Also search with the vocabulary those papers use. Then run `rank` → `coupling` → `show` again and
triage only the new candidates. Stop when a full round adds no new THREAT/DIRECT papers; this
usually takes 2–3 rounds. If the first round found nothing close, don't conclude the work is novel.
Try harder: use more generic mechanism queries, neighboring fields, and older terminology (pre-deep
learning names, statistics and control literature).

## Phase 7: Verify each paper you will report

- **Full text for THREATs and the top DIRECT papers.** Use WebFetch on `https://arxiv.org/abs/<id>`,
  `https://arxiv.org/html/<id>`, or the open-access PDF from `s2.py paper`. Compare against each
  contribution: same problem? same mechanism? same claimed result? what actually differs? Record
  the section or equation that overlaps.
- **Publication status.** `python3 $S/sources.py published "Exact Title"` checks DBLP, Crossref and
  S2 for a peer-reviewed version. Cite that version when it exists, and mark the paper "preprint"
  if not. A highly visible preprint can still be a THREAT; just say it is a preprint.
- **Date** against the cutoff (`publicationDate`, arXiv v1 date). Label post-cutoff work as concurrent.
- **Not already cited:** run `grep -i "<surname>" <bib files>` and check the year and title.
- **BibTeX** (DBLP first, then the publisher's version via Crossref/DOI, then arXiv):
  `python3 $S/sources.py bibtex <S2id|DBLP:key|DOI:x|ARXIV:x> ... --out $W/missing.bib`.
  Check that each entry matches the version you mean to cite.

## Phase 8: Report

Write `$W/report.md`, then give the user a summary of the top items with their paths. Use this
structure:

```markdown
# Missing related work: <draft title>
Audit <date>; cutoff assumed <date>; sources S2/arXiv/DBLP/Crossref/web; <N> queries,
<M> unique candidates screened, recall proxy <x%>.

## Bottom line
2–5 bullets: the biggest risks (e.g. "C2's 'first' claim is contradicted by [A]") and the count per category.

## 1. Novelty threats (must cite and differentiate)
### Author et al. (Year). Title. Venue [or arXiv preprint]. <DOI/arXiv/S2 link>
- **Overlaps with:** C2, "<quoted draft claim>" (Sec. 1)
- **What they do:** <2–3 sentences grounded in their abstract/method section, with section ref>
- **Remaining difference:** <honest assessment; "none apparent" if so>
- **Suggested fix:** cite in Sec. X; reword the claim to "…"; consider adding it as a baseline

## 2. Directly related work a reviewer will expect (should cite)
Grouped by theme; per paper: full reference + link, one line on why, where to cite.

## 3. Origins of methods, datasets, metrics used
## 4. Same idea in other communities
## 5. Authors' own prior work
## 6. Optional / lower priority (short)

## Notes
- Concurrent/post-cutoff work worth a mention
- In the .bib but never cited
- Statements about prior work that lack a citation (quote them, suggest refs if found)
- Cited preprints that now have a published version
- Searched and judged not missing (brief, so the user sees coverage)

## Limitations
Channels that failed or were rate-limited, unresolved bib entries, paywalled full texts not read.
```

Typical size: 0–5 threats, 5–20 should-cite papers, and a few optional ones. Don't pad. "No
novelty threats found after N queries and K rounds" is a valid result when it is true. Each claim
in the report must trace to something you read, and every paper needs an identifier (DOI, arXiv,
or S2 link).

## Pitfalls

- **Generic seeds:** forward citations of Adam, ResNet, BERT and similar papers are noise. Use the
  specific anchors.
- **Version confusion:** S2 usually merges arXiv and proceedings versions, but not always. Workshop
  versions, journal extensions and renamed papers may appear twice. Treat them as one paper and cite
  the archival version.
- **The draft itself** may already be on arXiv or OpenReview. `rank` marks it as `self` by title
  similarity; if it was renamed, recognize it by authors and abstract and exclude it.
- **Missing abstracts** (often for DBLP/Crossref-only records): use `s2.py paper`, the arXiv abs page,
  or WebFetch on the DOI landing page. Never judge from the title alone.
- **Rate limits and outages:** scripts retry with backoff. If S2 keeps failing, continue with
  arXiv/DBLP/Crossref and WebSearch, and say so under Limitations. If the DBLP search API is
  unreachable, `sources.py dblp` falls back to the SPARQL endpoint (`sparql.dblp.org`). Use
  `dblp-sparql --file q.rq` for custom queries, e.g. venue- or author-restricted ones with the
  `https://dblp.org/rdf/schema#` vocabulary (`dblp:title`, `dblp:publishedIn`,
  `dblp:yearOfPublication`, `dblp:authoredBy`, `dblp:primaryCreatorName`, `dblp:doi`).
- **Anonymity:** for double-blind drafts, suggest citing the authors' own work in the third person.
  Never suggest de-anonymizing.
