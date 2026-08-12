# Annotating sources with `changes.sty` (Mode A only)

Produce `main-annotated.tex` — a copy of the paper carrying tracked edits and margin comments, compilable two ways: showing the markup, and with every suggestion accepted.

Never edit `main.tex`.

## Setup

`cp main.tex main-annotated.tex`, then insert `assets/changes-preamble.tex`'s contents after the last `\usepackage` (typically after `xcolor`).

Use `commandnameprefix=always` so the commands are `\chadded`, `\chdeleted`, `\chreplaced`, `\chcomment`, `\chhighlight`. This avoids collisions — document classes and other packages commonly define `\comment` and `\highlight`.

## Commands

| Command | Use for |
|---|---|
| `\chreplaced[id=CL]{new}{old}` | A proposed rewrite. The workhorse. |
| `\chadded[id=CL]{text}` | A missing sentence, caveat, or limitation |
| `\chdeleted[id=CL]{text}` | Redundancy, changelog prose, overclaims |
| `\chcomment[id=CL]{short}` | A margin note. **Keep under ~15 words** — margins are narrow in two-column layouts. |
| `% CL: ...` | Rationale. Put the *reasoning* in LaTeX comments, not margin notes. |

The `% CL:` convention matters: the annotated PDF stays readable while the `.tex` carries the full argument for anyone reading the source. Use it for anything longer than a phrase.

## Multi-file papers

When the paper is one file per section, copy `sections/` to `sections-annotated/` and point `main-annotated.tex` at the copies (`sed 's|\\input{sections/|\\input{sections-annotated/|'`). Relative figure paths still resolve from the paper root. Do not annotate the originals.

## Document classes that forbid ulem — check first

`changes` loads `ulem` for strikeout, and some classes ban it. `aaai2027.sty` raises `! Package aaai Error: Package ulem is forbidden.` at `\begin{document}`.

For a review copy that will never be submitted, clear ulem's package marker so the class's check passes while ulem keeps working:

```latex
\makeatletter
\expandafter\let\csname ver@ulem.sty\endcsname\@undefined
\makeatother
```

Put it after loading `changes`, and comment loudly that it must never appear in a submitted file. Check the class for a forbidden-package list before assuming `changes` will load at all (`grep -n forbidden *.sty`).

## The \todo name clash

`changes` pulls in `todonotes`, which defines `\todo`. Many drafts define their own `\todo`. Symptoms and handling:

- `! LaTeX Error: Command \todo already defined.` → the paper defined it first. Free the name before loading `changes`: `\let\todo\relax`.
- **Do not then give the name back to the paper.** `\chcomment` calls todonotes' two-argument `\todo[opts]{text}`; a one-argument paper macro will render the option list as body text (`[TODO: []color=Changes@todocolor!10, ...`). Check for *live* uses first — in practice these macros only appear in commented-out prose, so letting todonotes keep the name is safe and correct.

## Gotchas, all encountered in practice

- **Multi-key `\cite` inside changes markup breaks.** `\chreplaced{...}{... \cite{a,b,c}}` produces `Undefined control sequence` and empty citations, because `ulem` re-scans the argument. Wrap it: `\mbox{~\cite{a,b,c}}`. Single-key cites usually survive, but wrapping is safer.
- **`\chhighlight` bleeds across column boundaries.** The `soul`-based highlight cannot break at a column break and will paint over the neighbouring column. Use `\chcomment` plus a `% CL:` note instead.
- **Preamble comments must be `%` comments.** `\chcomment` before `\begin{document}` does nothing.
- **Long unbreakable strings overflow.** DOIs and URLs inside `\chreplaced` cannot hyphenate. Add `\sloppy\emergencystretch=1em` to the enclosing group, or compare only the distinguishing suffix (`TVCG.2023.3326585` rather than the full DOI).
- **Character-level edits look terrible.** `Execution\chadded{-}\chdeleted{ }Verified` renders as `Execution-CL CLVerified`. Replace the whole token: `\chreplaced{Execution-Verified}{Execution Verified}`.
- **Set `\marginparwidth`** (≈1.6 cm) or margin notes overflow the page.

## The bibliography audit section

Add a `\clearpage`d `\section*{Bibliography audit}` before `\bibliography{...}`, marked clearly as a reviewer annotation to be deleted. Render each correction as markup so struck text is the current entry and blue text is the verified record:

```latex
\item \texttt{tang2023vistext} --- authors
\chreplaced[id=CL]{Benny J. Tang, Angie Boggust, Arvind Satyanarayan}%
                  {Tang, Linxi and Aleahmad, Toph and Heer, Jeffrey},
venue \chreplaced[id=CL]{ACL 2023, pp. 7268--7298}{CHI 2023}.
```

Do not use `\cite` here — typeset keys with `\texttt{}`. Wrap the list in `\begingroup\small\sloppy ... \endgroup`.

Placed just before the reference list, this section renders opposite the paper's own (wrong) bibliography, so the two can be compared on screen.

## Verify both compilations

```bash
latexmk -pdf -interaction=nonstopmode -outdir=/tmp/abuild main-annotated.tex
grep -nE "^! |LaTeX Error|Undefined control|Citation.*undefined" /tmp/abuild/main-annotated.log
```

Then try the accept-all path by adding `final` to the existing option list in a throwaway copy. **It may fail even when the markup version is clean** — in one case `changes` in `final` mode died with `Incomplete \iffalse` inside a `\chadded` that compiled fine in markup mode. If it fails, bisect by reverting annotations one at a time to find the trigger; if you cannot fix it, **say so in the review** and tell the authors to apply the suggestions by hand. Do not claim an accept-all build you did not produce.

A useful bisection shortcut: compile the *unannotated* document with the same `[final]` preamble. If that passes, the trigger is one of your annotations, not the class.

**Render the pages and look at them.** Markup that compiles can still be unreadable — overlapping margin notes, highlights crossing columns, edits that render as noise. Check visually before delivering.
