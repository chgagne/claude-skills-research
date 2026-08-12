# Bibliography audit

**Verify every entry against a primary source. No sampling.**

Errors cluster in the references authors were least likely to re-read — the classic, well-known papers everyone "knows". Those are exactly the ones a spot-check skips, and exactly the ones whose real authors may be reviewing the submission.

> **Mechanical verification lives in the `verifying-bibliography` skill** — the source
> ladder, the six fields, the fabrication signatures, the false-alarm patterns and the
> BibTeX comment traps. **Run it first**:
> `python3 ~/.claude/skills/verifying-bibliography/assets/run-bibcheck.py refs.bib --bbl main.bbl --out review-assets/`
>
> This file covers what the tool cannot do: turning its report into a review, judging
> selective citation, and writing `refs-corrected.bib`.

Reading the report: `CRITICAL`/`MAJOR`/`MINOR` are findings. `WEAK` and `UNVERIFIED` are
**not passes** — they are entries no database could confirm, which is precisely what a
fabricated reference looks like. Check them by hand and say in the review that you did.
`SKIP` entries (blogs, anonymous artifacts) need their URLs opened.

If the report warns that source coverage was degraded, re-run before trusting it.

## First, the mechanical cross-check

Before verifying content, confirm the `.bib` and the `.tex` agree:

```sh
grep -o "cite{[^}]*}" main.tex | sed 's/cite{//;s/}//' | tr ',' '\n' \
  | sed 's/ //g' | sort -u > /tmp/cited.txt
grep -oE "^@[a-z]+\{[^,]+," refs.bib | sed 's/^@[a-z]*{//;s/,$//' | sort > /tmp/defined.txt
comm -23 /tmp/cited.txt /tmp/defined.txt   # cited but undefined
comm -13 /tmp/cited.txt /tmp/defined.txt   # defined but never cited
```

This is cheap and catches a different class of problem than content verification. Uncited entries are dead weight; undefined ones are compile errors the author may not have noticed.

**Do it in Python, not shell.** Both files wrap: `@inproceedings{` and the key are often on separate lines, and `\bibitem[...]{key}` spans lines with `]` inside the brackets. Naive `grep -oE "^@[a-z]+\{[^,]+,"` silently misses entries and produces a wrong audit.

```python
import re, pathlib
bib = pathlib.Path('references.bib').read_text()
defined = set(re.findall(r'@\w+\s*\{\s*([^,\s]+)\s*,', bib))
bbl = pathlib.Path('main.bbl').read_text()          # authoritative: what actually rendered
cited = set(re.findall(r'\\bibitem\[.*?\]\{([^}]+)\}', bbl, re.S))
print(sorted(defined - cited))                      # dead weight
print(sorted(cited - defined))                      # should be empty
```

The `.bbl` is the ground truth for "actually cited", because it reflects the built document rather than every `\cite` including commented-out ones.

**An uncited entry can still be a finding.** Look at *what* is uncited. A present-but-uncited `oord2018infonce` next to a paper whose central loss is described as "an InfoNCE objective" means the core method has no attribution — invisible in the bibliography, visible in the text.

**Uncited entries are also unaudited.** Check the whole file, not only the cited subset. In one bibliography whose 35 cited entries had all been verified by hand, an uncited entry's DOI resolved correctly but its pages were 410–418 against the record's 411–419 — a defect that would have shipped had the entry ever been cited.

## Writing a corrected .bib

The two BibTeX comment traps (`%` does nothing inside an entry; an at-sign in between-entry text starts a new entry) are documented in `verifying-bibliography/reference/fabrication-signatures.md`.

Always compile the corrected file and check `.blg` for zero errors before delivering it. Move any stale `main.bbl` aside first, or your test will silently pass by using the old one.

**Prefer the venue of record.** Where a paper has both an official publication (workshop, conference or journal) and a preprint, the corrected entry cites the **published version** — it is peer-reviewed, has stable pagination, a DOI, and correct venue metadata. Keep the preprint in the same entry as a supplementary `url`/`eprint`; an entry that names its venue *and* carries `eprint` is the target state, not a defect. `verifying-bibliography` reports these as `preprint` findings.

## Also check: selective citation

Metadata correctness is not citation correctness. For each load-bearing citation, read at least the cited paper's abstract and ask: **does the submission's characterisation survive it?**

The specific failure to look for is a paper cited only for its favourable half — the submission quotes the positive finding and omits the caveat that the cited authors themselves foregrounded. This is a genuine finding, it is easy to verify, and a reviewer who knows that paper will catch it.

## Deliverables

**1. An audit table in the review**, grouped by severity:

```markdown
### Material errors (N)
| Key | Problem | Correct |
|---|---|---|

### Minor (N)
### Correct as written (N)     <- list them; it shows coverage
### Unverifiable by construction (N)
### Selective citation
```

Listing the correct entries matters: it demonstrates you checked everything rather than only reporting hits.

**2. `refs-corrected.bib`** (Mode A) — a drop-in replacement:

- **Keep the cite keys identical** so it swaps in with `\bibliography{refs-corrected}` and no `.tex` edits
- Give every corrected entry a `% FIXED:` comment naming exactly what changed, so the authors can audit rather than trust
- Mark correct entries `% CORRECT AS IS` so coverage is visible in the file
- For unverifiable entries (anonymous artifacts), leave them as submitted and comment on what the text must say instead
- **Verify it compiles**: back up `refs.bib`, swap in the corrected file, run `latexmk`, confirm zero undefined citations, then restore the backup

**3. Markup in the annotated document** (Mode A) — see `annotating-with-changes.md`. Render each correction as `\chreplaced{correct}{wrong}` and use `\chcomment` where no correction is possible. Placing this section next to the paper's own reference list lets the reader compare directly.

## Unverifiable entries

Anonymous repositories, artifacts under review, personal communications. You cannot fix these. Instead:

- State plainly that nothing about them can be checked externally
- Check whether such an entry carries load — if the paper's main comparison rests on an unverifiable artifact, that is a major concern, not a bibliography note
- Check that any URL still resolves
