# Fabrication signatures and BibTeX traps

## The LLM-generated bibliography signature

Watch for this pattern, which indicates the `.bib` was generated rather than exported:

- Recent arXiv entries perfectly correct (they were in the model's context)
- Classic papers with **plausible but invented titles** — a title that describes the paper
  accurately but is not what it is called
- **Author lists transplanted between entries** — entry X carries entry Y's authors verbatim
- **Fabricated co-authors** who are real, prominent people in the field but not on that paper
- Author name forms subtly wrong (`Bakker, Alex` for `Bakker, Michiel A.`)
- Plausible-looking but wrong page ranges

When you see two or more of these, say so in the review and ask how the file was assembled.
It changes the reviewer's prior on everything else in the paper.

## A correct DOI beside a wrong title

**This is the signature of a fabricated entry.** The DOI was retrieved; the title was
invented around it. Always check both — checking authors alone is the most common way to
miss it.

Measured instance: `moritz2019draco` carried DOI `10.1109/TVCG.2018.2865240`, which is
**correct** and resolves to *"Formalizing Visualization Design Knowledge as Constraints:
Actionable and Extensible Models in Draco"*. The `.bib` title was *"Draco: An Approach to
Generating Visualizations with a Computational Design Process"* — a title that describes the
paper but is not its name. Volume and pages were wrong too (26/661–671 against the real
25/438–448).

**The stronger version: a DOI pointing at an entirely different paper.**
`wongsuphasawat2016voyager` carried `10.1109/TVCG.2015.2467251`, which resolves to
*"High-Quality Ultra-Compact Grid Layout of Grouped Networks"* by Yoghourdjian, Dwyer, Gange,
Kieffer, Klein and Marriott — no author in common with the Voyager entry. The correct DOI is
`...2467191`. The entry also invented two co-authors (Bach, Dragicevic) and dropped a real
one (Howe).

A title-search tool scored that entry **0.83** and cleared it.

## False-alarm patterns that are *not* findings

Each of these was observed producing a false positive. Normalise them away rather than
reporting them.

| Pattern | Example | Handling |
|---|---|---|
| DBLP disambiguation suffix | `Elena Rossi 0001` | strip trailing ` \d{4}` |
| LaTeX escapes undecoded | `Dupr\'e`, `Kulh{\'a}nek`, `Jon{\'a}{\v{s}}` | decode to Unicode, then accent-fold |
| Initials-only vs full name | `Dupré, B.` vs `Benoit Dupré` | match on family name; given names only break ties |
| Compound surname across name orders | `Molina León, Gabriela` vs `Gabriela Molina León` | key on the final token of the family part |
| HTML-escaped / typographic apostrophes | `O&apos;Reilly` vs `O’Reilly` | HTML-unescape and fold quote characters |
| Two authors sharing a family name | Hengzhe Zhang **and** Mengjie Zhang | compare given initials as a *set* per family |
| Preprint year vs published year | DMLR 2024 cited, indexes say 2022 | compare year only against strong, non-preprint records |
| Book editions and reprints | Strogatz 1994 vs a 2024 printing | `@book` year differences are `MINOR`, never `MAJOR` |
| arXiv DOIs | `10.48550/arXiv.2601.23265` | DataCite, not Crossref — route to the arXiv API |
| Venue punctuation | `Linguistics: ACL 2024` vs `Linguistics ACL 2024` | strip punctuation before the containment test |
| Preprint record venue | arXiv record reports `venue = arXiv` | never compare venue against a preprint record |
| Year-as-volume | `volume = {2025}` on a 2025 ICLR paper | artifact — but **NeurIPS vol 35 is legitimate**, so fire only when the volume equals the year |

That last row matters: *Advances in Neural Information Processing Systems* genuinely is a
numbered series, so "conference papers have no volumes" is false. The artifact is
specifically the publication **year** appearing in the volume field.

## Establish identity before comparing anything

The single most repeated mistake while building this tool was comparing a field against a
record that describes a **different work**. It appeared three times, each time looking like
a plausible finding:

- DBLP answered *"Semantic genetic programming"* with a 2019 EuroGP paper on Cartesian GP;
  the year comparison then reported a 3-year error in a correct entry.
- DBLP matched a *SIAM Review* review of Strogatz's textbook against a *Physics Today*
  review of it; volume and pages disagreed, meaninglessly.
- DBLP answered the InfoNCE preprint with *"Self-Supervised **EEG** Representation Learning
  with Contrastive Predictive Coding"*, which the tool nearly reported as InfoNCE's
  published version — sending the author hunting for a paper that does not exist.

The rule: **a record earns the right to be compared only once its title matches.** A trusted
source is not enough; DBLP produced all three of the above. Where identity cannot be
established, report `WEAK` and stop, rather than emitting confident-looking field
disagreements.

## The `.bbl` is ground truth for "cited"

`\bibliography{...}` inputs `./main.bbl`, so a leftover `.bbl` silently shadows a corrected
bibliography even with `-outdir`. Delete or move it aside before testing. This also explains
a real class of defect: a submission built past a fatal error against an old `.bbl` ships a
bibliography that no longer matches its own citations.

```python
import re, pathlib
bib = pathlib.Path('references.bib').read_text()
defined = set(re.findall(r'@\w+\s*\{\s*([^,\s]+)\s*,', bib))
bbl = pathlib.Path('main.bbl').read_text()          # what actually rendered
cited = set(re.findall(r'\\bibitem\[.*?\]\{([^}]+)\}', bbl, re.S))
print(sorted(defined - cited))                      # dead weight
print(sorted(cited - defined))                      # should be empty
```

Do this in Python, not shell: both files wrap lines, `@inproceedings{` and the key are often
on separate lines, and `\bibitem[...]{key}` spans lines with `]` inside the brackets. A naive
`grep -oE "^@[a-z]+\{[^,]+,"` silently misses entries and produces a wrong audit.

**An uncited entry can still be a finding.** Look at *what* is uncited. A present-but-uncited
`oord2018infonce` beside a paper whose central loss is described as "an InfoNCE objective"
means the core method has no attribution — invisible in the bibliography, visible in the text.

Uncited entries are also unaudited. `caetano2023trees` sat uncited in a bibliography whose
35 cited entries had all been verified by hand; its DOI resolves correctly but its pages were
410–418 against Crossref's 411–419. Run the checker over the whole file, not only the cited
subset.

## Two BibTeX rules that will bite you when writing a corrected file

BibTeX comments are not LaTeX comments.

1. **`%` does nothing inside an entry.** A `% FIXED:` note placed between two fields makes
   BibTeX fail with `I was expecting a ',' or a '}'`. Every note must sit *between* entries.
2. **An at-sign in between-entry text starts a new entry.** Writing
   `% near-duplicate of the @book entry` produces `I was expecting a '{' or a '('`. Keep
   at-signs out of comments entirely.

Always compile the corrected file and check `.blg` for zero errors before delivering it.
Move any stale `main.bbl` aside first, or the test silently passes using the old one.
