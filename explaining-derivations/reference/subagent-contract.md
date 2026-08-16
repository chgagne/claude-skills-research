# The per-theorem subagent contract

Versioned: `explain-request/1` in, `explain-fragment/1` out.

**The subagent writes no files.** It returns one JSON object. The dispatcher owns
all I/O, and that is what makes assembly deterministic, notation collisions
detectable, and a stale explanation refusable rather than silently attached to a
step that has since changed.

## In — `explain-request/1`

Written by the tool into `<out>/requests/<claim>.json`.

```json
{
  "request_id": "claim/thm:elbo",
  "contract": "explain-request/1",
  "level": "grad-ml",
  "claim":  { …the ledger claim verbatim: statement, hypotheses, conclusion… },
  "proof":  { …the ledger proof, including its structure and any hedges… },
  "steps":  [ …every step to expand, verbatim, in order… ],
  "notation": {
    "macros":  { …the frozen macro table… },
    "symbols": [ {"symbol": "\\gamma", "domain": "unit-interval-half-open",
                  "domain_provenance": "declared",
                  "quote": "$\\gamma \\in [0,1)$"} ],
    "preamble_packages": ["geometry", "amsmath", "amssymb", "amsthm", …],
    "macro_rule": "…rewrite anything these do not provide into plain amsmath…",
    "forbidden_new_macros": true
  },
  "context": {
    "definitions":        [ …definition claims… ],
    "assumptions":        [ …assumption claims in scope… ],
    "referenced_results": [ {"label": "lem:2", "statement_tex": "…", "local": true} ]
  },
  "verdicts": {
    "proof/thm:elbo/s07": {"verdict": "MAJOR", "engine": "sideconds",
                           "script": "checks/proof-thm-elbo-s07.py"}
  },
  "move_vocabulary": ["substitute-definition", "algebraic-rearrangement", …],
  "budget": {"max_tool_calls": 40, "wall_clock_s": 600},
  "output_contract": "explain-fragment/1"
}
```

**`preamble_packages` is not decoration.** `macros` holds what the *paper*
defines with `\newcommand`; it says nothing about what those definitions are
built on. A paper loading `\usepackage{physics}` writes `\dd t` in every step of
an SDE proof and records it nowhere, so a fragment that copies the step verbatim
returns valid JSON that assembles into a document dying on `Undefined control
sequence` — after the expansion, the expensive part, has been paid for. The list
is read out of `templates/preamble.tex` at request time rather than hard-coded,
because a list that drifts from the file it describes is a list that lies.

`--verdicts` takes `proofsteps.csv`, **not** `proof-ledger.json`. The two sit
side by side in `review-assets/` and only the first carries verdicts; passing the
second used to load as an empty mapping, which produces a whole document of *not
run* cells indistinguishable from a paper on which no engine could fire. It is
now refused with a message naming the right file.

**`verdicts` is the join with `verifying-proofs`.** If the checker ran, the
*Checked* column is filled from real evidence. If it did not, `verdicts` is `{}`
and **every *Checked* cell must read `not run`** — the expander is forbidden to
write a mechanical verdict it did not receive, and `fragment.py` refuses a
fragment that does.

## Out — `explain-fragment/1`

One fenced JSON object, returned to the dispatcher.

```json
{
  "request_id": "claim/thm:elbo",
  "contract": "explain-fragment/1",
  "tex_fragment": "…optional prose to place before the steps…",
  "rows": [{
    "step_id": "proof/thm:elbo/s07",
    "content_hash": "9e6990b9579c38d5",
    "before_tex": "\\mathbb{E}\\left[\\sum_i f(x_i)\\right]",
    "after_tex":  "\\sum_i \\mathbb{E}[f(x_i)]",
    "move": "linearity-of-expectation",
    "licensed_by": {"kind": "named-result", "value": "linearity-of-expectation"},
    "breaks_if": "the sum is infinite, so the interchange needs a dominating bound",
    "checked": {"verdict": "MAJOR", "engine": "sideconds",
                "script": "checks/proof-thm-elbo-s07.py"},
    "gloss": "Averaging a total is the same as totalling the averages, as long as there are finitely many terms.",
    "expanded_into": ["…optional sub-steps, when one move is really three…"]
  }],
  "gaps": [{
    "step_id": "proof/thm:elbo/s11",
    "severity": "BLOCKING",
    "kind": "cannot-justify",
    "what_is_missing": "the exchange of $\\lim$ and $\\sum$ at (14)",
    "what_would_close_it": "a dominating summable bound, or uniform convergence on the index set",
    "quote": "Taking limits on both sides, we obtain"
  }],
  "symbols_introduced": [{"symbol": "\\tilde{q}", "why": "the normalised iterate",
                          "defined_in_fragment": true}],
  "macros_requested": [],
  "self_check": {"rows_cover_all_inference_steps": true, "unexplained_steps": 0,
                 "forbidden_tokens_present": false}
}
```

## What the validator refuses

| Refused | Why |
|---|---|
| `licensed_by` outside the four kinds, or free text | A free-text justification field is how an unchecked step acquires a confident-sounding reason. |
| A `checked` verdict not present in the request's `verdicts` | Inventing evidence inverts the purpose of the skill. |
| A stale or missing `content_hash` | The explanation would attach to a step that has since changed. |
| A `step_id` not in the ledger | The row explains something that is not in the paper. |
| `\usepackage`, `\documentclass`, `\newcommand`, `\def`, `\begin{document}` | A fragment is a body, not a document. Use `macros_requested`. |
| A gap severity outside `BLOCKING`/`SUBSTANTIVE`/`NOTATIONAL`/`COSMETIC` | The roll-up and the review mapping both key on it. |
| A `BLOCKING` or `SUBSTANTIVE` gap with no `what_would_close_it` | A gap that names no remedy cannot be acted on. |

## What it warns about but keeps

- An **off-vocabulary move**. Flagged, never dropped: losing the row would lose
  the explanation, and the point of the warning is to notice drift so the
  vocabulary can be extended deliberately.
- A row with an empty `breaks_if`. Every move has a way to fail; silence there
  usually means the move was not thought through.
- A `macros_requested` entry missing a name or a body.

## Instructions to give the subagent

Alongside the request, pass the register contract from `reference/registers.md`
and the move list from `reference/move-vocabulary.md`, plus these standing rules:

1. **Every inference step in `steps` gets a row.** If a step cannot be explained,
   it gets a gap — not silence.
2. **`not-established` is a correct answer.** Prefer it, loudly, over a plausible
   reason you cannot point at.
3. **Do not introduce notation.** Use `macros_requested` if you genuinely need a
   symbol; the dispatcher grants it for every document or refuses once.
   Everything you write is typeset against `notation.preamble_packages` and
   `notation.macros` and nothing else — rewrite any control sequence outside them
   into plain amsmath (`\dd t` becomes `\mathrm{d}t`) rather than requesting a
   macro for something amsmath can already write.
4. **Do not report a verdict.** Copy what the request gave you, or leave it.
5. **A `BLOCKING` gap must say what would close it.** "This is unclear" is not a
   finding; "this needs a dominating summable bound" is.
6. **If you cannot finish, return what you have plus `BLOCKING` gaps.** A partial
   expansion with an honest ledger is worth more than a complete-looking one.

## Retry policy

One silent retry on a fragment that fails validation, with the problems appended
to the request. A second failure produces a document titled *"This derivation
could not be expanded"* carrying whatever rows survived and the gap ledger.

That is the thesis in operation: the skill does not quietly produce a shorter
document, it produces a document that says what it could not do.
