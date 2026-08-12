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
because a scalar hides exactly what matters.

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
