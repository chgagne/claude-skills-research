# md2pdf

Render Markdown to PDF via pandoc + XeLaTeX. One self-contained script: the
LaTeX preamble and the Lua filters are embedded and written to a temp dir per
run, so the file can be copied anywhere on its own and still work.

```sh
md2pdf notes.md                        # -> notes.pdf
md2pdf -o out.pdf notes.md
md2pdf --review review-me-20260815.md  # paper-review profile
md2pdf a.md b.md c.md                  # batch; one failure does not stop the rest
md2pdf --help
```

Requires `pandoc` and `xelatex`. **Never install either without asking the
user.** Fonts are probed at runtime — `fc-list` for system fonts, `kpsewhich`
for TeX Live fonts, which is necessary because TeX Gyre, DejaVu and Latin
Modern are invisible to fontconfig on macOS. Whatever is missing degrades to
the next candidate rather than failing.

## Which skills use it

- `reviewing-paper-sources` — phase 6, the review `.md` and its audit reports
  (`--review`)

## The `--review` profile

Adds four things and changes nothing else:

- **Metadata block.** A run of `**Label:** value` lines breaks per label while
  wrapped continuation text keeps flowing.
- **Blockquote → callout box.** A review's repository-state note is an action
  item; it must not read as ordinary prose.
- Denser tables (`tabcolsep 5pt`, `arraystretch 1.15`).
- 2cm margins, because dense audit tables need the width.

## Things learned the hard way

Each of these came from a real failure; changing them will reintroduce it.

- **Do not use pandoc's `hard_line_breaks`** to fix the metadata block. It
  breaks at *every* newline, so a hard-wrapped paragraph becomes a column of
  ragged short lines. The `--review` filter breaks only where a new `**Label:**`
  begins.
- **Do not map a Unicode symbol to its LaTeX command.** Under `unicode-math`,
  `\sum` *is* U+2211, so `\newunicodechar{∑}{\ensuremath{\sum}}` expands to
  itself until TeX exhausts main memory. Look the glyph up by codepoint in an
  explicit font instead — `\char` leaves nothing to re-expand. For the same
  reason the large operators (`\sum`, `\prod`, `\int`) are deliberately *not*
  remapped: wrapping them costs their `\limits` placement.
- **Do not use `pifont`** for check marks and crosses. Its `\ding` glyphs come
  from Zapf Dingbats, whose PDF text layer extracts as ASCII — a check mark
  copy-pastes out of the finished PDF as `3`. DejaVu Sans has the real
  codepoints.
- **`raw_tex` stays off.** Otherwise prose that merely *mentions* `\citet` or
  `0.88\textwidth` is executed and aborts the build. Notes about LaTeX papers
  do this constantly. `$...$` math is a separate extension and still renders.
- **Guard anything that touches `longtable`.** Pandoc loads that package only
  when the document actually contains a table, so `\setlength{\LTpre}{...}` in
  the preamble kills every table-less document.
- **A missing glyph is dropped silently** by the engine — the character is
  simply absent and the sentence reads as if it was never written. Every
  dropped character is therefore reported on stderr. Do not silence it.
- **`grep -q` under `set -o pipefail`** reports failure: it exits early, the
  upstream process takes SIGPIPE, and `pipefail` surfaces that. This silently
  broke every font probe once. Use `grep -c` and test the count.
- **Empty arrays under `set -u`** abort on bash 3.2 (macOS system bash).
  Expand as `${arr[@]+"${arr[@]}"}`.

## Automatic behaviour worth knowing

Long unbreakable tokens (DOIs, URLs, identifiers) get break opportunities
inserted; without this a DOI in a narrow table column runs past the margin.
Section numbers are suppressed when the document already numbers its own
headings. A macro the document quotes but never defines is learned from the
error log, typeset as its own name, and the build retried; if math still will
not compile, a final pass typesets that math as source text and says so.

## Verified against

27 Markdown files of real review material (304 pages): all 27 build, 5
residual overfull boxes with a worst case of 0.2in, and one unrenderable
character (a colour emoji, which XeLaTeX cannot do) which is reported.
