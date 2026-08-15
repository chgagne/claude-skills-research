# claude-skills-research

Claude Code skills for supporting academic research in machine learning and computer
science: reviewing papers, verifying bibliographies, finding related work, comparing a
draft against prior art, and running experiment campaigns on HPC clusters.

These grew out of real reviewing work. Every design decision that looks odd is there
because something failed on a real paper, and the reasoning is recorded in the skill
itself rather than lost.

## Install

```sh
git clone https://github.com/chgagne/claude-skills-research ~/.claude/skills
```

Or clone elsewhere and symlink the ones you want into `~/.claude/skills/`. Claude Code
discovers a skill by the frontmatter in its `SKILL.md`.

**No dependencies.** Every tool is Python 3.10+ standard library only — no pip install, no
virtualenv. A guard test in each skill fails the suite if a third-party import creeps in.

### Optional configuration

| Setting | Effect | How |
|---|---|---|
| `SCHOLARLY_MAILTO` | Puts Crossref/OpenAlex requests in their *polite pool* — faster and more reliable. Optional; everything works without it. | `export SCHOLARLY_MAILTO="you@university.edu"` or write it to `~/.config/scholarly/mailto` |
| `S2_API_KEY` | A dedicated 1 req/s lane on Semantic Scholar instead of a contended anonymous pool. | [Request one free](https://www.semanticscholar.org/product/api#api-key-form), then `export S2_API_KEY=…` or `~/.config/scholarly/s2_key` |
| `pdftotext` | Lets `comparing-papers` read PDFs when LaTeX source is unavailable. | `brew install poppler` / `apt install poppler-utils` |
| `sympy` | Lets `verifying-proofs` confirm an algebraic identity rather than merely failing to refute it. Absent, those steps report `UNVERIFIED` and the run exits 2. | `pip install sympy` |
| `z3` | An opt-in escape hatch in `verifying-proofs` for a concrete inequality over reals or integers. Not used by any default run. | `pip install z3-solver` |
| `latexmk` | Builds the per-theorem PDFs in `explaining-derivations`. Absent, the `.tex` is still written and the run exits 2. | any TeX distribution |

The proof skills **never install any of these**. A missing checker is a question
for you, and the run degrades — naming what it could not check — rather than
failing or pretending.

API responses are cached under `~/.cache/scholarly/`, so re-runs across drafts are close to
free.

## The skills

### Paper review

**`reviewing-paper-sources`** — the orchestrator. An eight-phase review that treats a paper
as an evidence-gathering exercise rather than a reading exercise: compile the sources
yourself, render the figures, recompute the headline statistic, audit every reference.
Phase 0 asks which optional modules below to run. Handles both internal review (a
colleague's draft, with proposed fixes) and external refereeing (diagnosis only).

**`verifying-bibliography`** — finds incorrect and fabricated references. Resolves a stable
identifier first, then compares the record *back* against the `.bib`. That inversion is the
whole point: searching by the title you are trying to verify is circular, and a fabricated
title that accurately describes the right paper will retrieve it and pass. Reports author
problems as set differences (`+Bach, +Dragicevic, −Howe`) rather than a similarity score,
because a scalar hides exactly what matters. Considerable care goes into *not* crying wolf:
BibTeX's `and others`, LaTeX ties inside surnames, Unicode dash variants, records held in
another script, and institutions listed where a `.bib` lists people are all normalised away,
because a checker that reports fabrication on `and others` teaches its user to ignore it.

**`surveying-literature`** — finds work a draft should have cited, and maps fields. Expands
through the citation graph *and* searches the draft's own topic across five heterogeneous
engines (Semantic Scholar, OpenAlex, arXiv, Crossref, DBLP), then grades candidates by how
much they threaten the novelty claim. The topical path matters because graph traversal
cannot reach what a thin related-work section is not already near — and a thin related-work
section is the defect being looked for.

**`comparing-papers`** — puts a draft and its closest prior work side by side on the axes
reviewers attack: training scale, seeds, compute, protocol, metrics. Fetches LaTeX source in
preference to PDFs, because the numbers that decide reviews live in appendices. Computes a
note only where the relation is arithmetic — a scale ratio, a seed count — and elsewhere
shows two quoted passages and stops, because "these protocols differ" is a judgement.

**`verifying-proofs`** — checks the mathematics rather than the claims. The
design inversion is that it refuses to translate LaTeX into a computer algebra
system: `parse_latex` needs `antlr4` and its grammar has no expectations, no
`\operatorname{}`, no norms and no user macros, so a translator's bugs would
surface as false counterexamples — the one failure a proof checker cannot
survive. Instead it writes one auditable check script per step, carrying the
source LaTeX, each symbol's domain **and where that domain came from**, and the
side conditions the step needs. A symbol whose domain the paper never stated can
never produce a counterexample; on one real paper 54 of 61 symbols were in that
position, and sampling them freely would have manufactured dozens of errors
against correct mathematics. Its default mode needs nothing external at all and
still finds inductions with no base case, claim dependency cycles, restatements
that drop a hypothesis, and divisions by quantities nobody proved non-zero.

**`explaining-derivations`** — expands a proof into a standalone document making
every step explicit, for a reader without formal mathematical training. It is not
only pedagogy: **an expansion that cannot be completed is evidence against the
derivation.** A step nobody can justify explicitly leaves the document as a
gap-ledger row with a severity, and that ledger feeds back into the review. Each
step is rendered as what changed, why the move is licensed, what would break it,
and what a checker made of it — with `licensed by` restricted to a closed set of
four shapes, because a free-text justification field invites a plausible-sounding
reason for a step nobody checked.

### Research workflow

**`collaborating-on-research`** — working with a researcher across many sessions: choosing
directions, deciding whether to ask or act, recording what was decided, and writing up
results so they survive the session that produced them.

**`running-cluster-experiments`** — planning and running multi-job experiment campaigns on
Slurm: sizing walltime, shaping arrays, deciding what to submit first, and diagnosing jobs
that hit walltime, produced nothing, or silently ran the wrong configuration.

**`using-drac-clusters`** — the Digital Research Alliance of Canada systems (Narval,
Rorqual, TamIA, Fir, Nibi, Trillium). Encodes one national HPC system's conventions —
authentication, per-cluster filesystem layouts, allocation accounts — so adapt it if you
are on a different facility.

### Shared

**`_shared/scholarly/`** — the retrieval layer every paper skill imports: per-host
throttling, retries with capped backoff, a circuit breaker, on-disk caching, LaTeX handling
and BibTeX parsing. Not a skill; it has no `SKILL.md`.

**`_shared/latexmath/`** — the proof-parsing layer, turning LaTeX into a step
ledger: theorem environments, proof segmentation, `align` chain reconstruction,
the `\label`/`\ref` graph, a symbol inventory carrying each domain's provenance,
and the side conditions a step requires. Consumed by `verifying-proofs` and
`explaining-derivations`. Not a skill; it has no `SKILL.md`.

## Design principles

These are worth stating because they are what the skills are actually made of.

**Identity before use.** Never compare a field against a record until the title matches. The
recurring bug in this codebase was confidently reporting a difference between two *different
papers* — a database answering "Semantic genetic programming" with a Cartesian GP paper, or
the InfoNCE preprint with an EEG paper of a similar name.

**Report what you could not verify.** `WEAK` and `UNVERIFIED` are findings, not passes. A
fabricated reference is precisely the one no database can find, so silence is the signal.

**Evidence, not judgement.** Tools compute what is arithmetic and quote what is not. A
number without its source sentence is unusable in a review, because the first question is
always "where does that come from".

**Fail loudly when a source is down.** Silent degradation changes findings: two consecutive
runs once produced 8 findings then 7 purely because one index dropped connections. Failures
are counted, reported, and set exit code 2.

**Say what the tool cannot do.** Each skill has a Limits section naming its real failure
modes, including ones that were tried and not solved.

**Every rule earns its place on real data.** The false-alarm tables, the retry and
circuit-breaker settings, and the LaTeX gotchas are all things that went wrong on an actual
paper; each carries the case that produced it, so a future reader can tell a considered
choice from an arbitrary one.

## Contributing

Every tool is test-driven; suites run offline in seconds:

```sh
cd <skill>/assets && python3 -m unittest discover -s tests
```

If you change extraction or matching behaviour, add a test with a *real* example — the
false-alarm tables in these skills are all drawn from things that actually went wrong.

## Author

Christian Gagné — Université Laval.
Built with Claude Code; the design rationale in each skill records what failed on real papers and why the current approach replaced it.

## License

MIT.
