# Writing report template

`render-ledger.py` produces this file; the template documents the shape so a reader
knows what each part means. Rendered with `_shared/md2pdf/md2pdf --review`.

```
# Writing report

**Paper:** main.tex            the file proofread
**Mode:** A                    A = internal (annotated copy), B = external (report only)
**Date:** YYYY-MM-DD
**Field profile:** <slug>      or "none": defaults only
**Author profile:** <slug>     or "none"
**Markup build:** passed|failed|not run
**Accept-all build:** passed|failed|not run
**Dropped to make the build pass:** flow, framing     present only when the bisect dropped levels

## Run rules              from the calibration sample, verbatim
## Counts                 applied / degraded / cut, per level
## Mechanics              one ### W<n> entry each: Before, After, Why, Rule (confidence)
## Sentence clarity and style
## Paragraph and argument flow        comment-only: Before is the paragraph's first sentence
## Terminology and framing
## Cut by the noise gate or unanchored     table: id, level, reason, anchor
```

Reading order for authors: Counts, then Framing (paper-wide), then Flow, then Style,
then apply Mechanics last in the tex. Every `W<n>` in a margin of the PDF is a heading
here.
