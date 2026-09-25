# Building style profiles

Two profiles, both private, both markdown, both cached outside this repository under
`$STYLE_PROFILES_DIR` (default `~/Claude/style-profiles`). The skill never ships one.

```
$STYLE_PROFILES_DIR/
  sources/<arxiv-id>/source.tex, meta.json     fetched e-prints
  fields/<slug>/stats.md, profile.md            field standard
  authors/<slug>/stats.md, profile.md           author voice; slug is a nickname, not a name
  preferences.md                                confirmed rules
  preferences-pending.md                        candidate rules awaiting confirmation
```

## 1. Propose the corpora

Field: `python3 assets/fetch-corpus.py --dest $STYLE_PROFILES_DIR/sources --propose references.bib --venue ICLR --venue NeurIPS --venue ICML`
prints bibliography entries at the target venues that carry an arXiv id. Keep 5–8:
prose-heavy, well cited, same subfield. Author: `--author "<name>" --limit 5` lists the
authors' prior papers by citation count (needs `S2_API_KEY`). Show both lists to the user
in one AskUserQuestion and take their edits. In a blind Mode B review, skip the author
profile.

## 2. Fetch

`python3 assets/fetch-corpus.py --dest $STYLE_PROFILES_DIR/sources --arxiv <id> <id> ...`
One request per id, 3 s apart, cached on disk. An id with no LaTeX source prints
`NO LATEX SOURCE`; run `reviewing-paper-sources/assets/run-pdfshim.py` on the PDF and
save its `body-*.txt` concatenated as `source.tex` in the same directory, with `meta.json`
saying `"kind": "pdfshim"`.

## 3. Statistics

`python3 assets/profile-stats.py $STYLE_PROFILES_DIR/sources/<id> ... --out $STYLE_PROFILES_DIR/fields/<slug>/stats.md --title "<slug>"`
Pooled first, then per paper. Read the pooled block; if one paper is an outlier on
passive rate or sentence length, say so in the profile.

## 4. Distil

One subagent, given `stats.md` and the sources, writes `profile.md` with this shape:

```
# Style profile: <slug>          (field | author), built YYYY-MM-DD from N papers

## Register (from stats.md)     sentence length, passive rate, first person, hedges,
                                intensifiers, tense by section, cross-reference form
## Conventions                  keyed rules the workers can cite as field:<key> /
                                author:<key>, e.g. `field:number-first` "results
                                sentences open with the number"
## Exemplars                    2–3 sentences per rhetorical move, each with its source id:
  - stating the problem
  - stating a contribution
  - introducing a method component
  - describing a figure
  - reporting a result with a number
  - admitting a limitation
  - positioning against related work
## Avoid                        constructions the corpus never uses
```

Keys under Conventions are what ledger rows cite. Exemplars are quoted from published
papers, which is fine; never quote the draft under review into a profile.

## 5. Reuse

Point later runs at an existing slug when the subfield or authors match. Rebuild when the
venue changes or the corpus grows by more than half.
