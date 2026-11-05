# Protocol R3: a fixed review form for reviewing-paper-sources

Written 2026-11-04, after R2 and before any change to the skill. The researcher chose the form
("fixed sections + checklist") and the primary criterion ("structure + coverage"); the rest is
Claude's default.

## Why

R2: the skill raised coverage (0.89 vs 0.81) but did not make reviews more alike, and its
reviews varied *more* in structure than the bare agent's (heading Jaccard 0.21 vs 0.31), because
the template says "adapt freely". The researcher's aim is a standard review that comes out the
same way each time. The series' lesson is that structure the agent must answer is executed and
prose is not, so the form comes with a validator the agent must run.

## Change (branch `review-form`)

- `reference/review-template.md`: the twelve level-2 headings become mandatory, verbatim, in this
  order: `1. Summary of the submission`, `2. Overall assessment`, `2a. Coverage checklist`,
  `3. Strengths`, `4. Major concerns`, `4a. Not written yet`, `5. Bibliography audit`,
  `6. Figures and tables`, `7. Detailed comments by section`, `8. Writing, formatting, and
  mechanics`, `9. Action plan`, `10. Questions for the authors`. A section with nothing to say
  keeps its heading and states why in one line ("Not run: out of scope", "Not applicable:
  finished paper"). Lifecycle-specific titles move into the section's first line.
- `2a. Coverage checklist`: a 14-row table (the R2 checklist items), columns `#`, `Item`,
  `Status` (`done` / `issue` / `n.a.`), `Evidence` (what was checked, or why n.a.; a finding
  label where the item produced one).
- `assets/check-review-form.py <review.md>`: reports missing, renamed or out-of-order headings,
  checklist rows missing or without status or evidence, and a §2 without its `Recommendation:`
  and disqualifying lines; exit 0 and `OK` when clean. Stdlib only, offline tests.
- SKILL.md phase 6: write the review in the form, run the checker, fix until `OK`.

## Dev (tuning allowed)

Drafts 54 and 109 (R2 material), 2 runs each with the changed skill. **Dev gate:** checker `OK`
at the end of 4/4 runs and the 12 headings identical in all 4. At most two dev rounds; if the gate
fails twice, back to the researcher.

## Test

Drafts: 134 and 179 (carry R2's 7-error gold list; never used for tuning) and four fresh
disguised, probed drafts from the C2 pool, unplanted originals: 144, 177, 108, 116. Arms:
`form` (branch `review-form`, frozen at test build), `current` (cc5bb1d) and `without`,
**3 runs each per draft: 54 runs** (about $70). Same prompt, tools and limits as R2.

## Criteria

- **Primary (structure):** in the `form` arm, the level-2 heading sequence is identical across
  the 3 runs in at least 5 of 6 drafts, and the checker passes at the end of at least 17 of 18
  runs.
- **Primary (coverage):** judged coverage (R2 judge, R2 checklist) `form` at least `current`
  minus 0.02, and at least `without` plus 0.05.
- **Guard:** gold recall on 134 and 179, `form` at least `without` minus 0.10.
- Secondary: finding agreement (R2 rule), heading Jaccard, verdict agreement, cost (`form` at
  most 1.3 x `current`), coverage on the 9 generic items.

The coverage gain is partly by construction (the form asks for the items the judge looks for);
the judge requires a substantive treatment, and the generic-only coverage is reported for that
reason.

| Outcome | What follows |
|---|---|
| all primary and guard met | merge `review-form`, measured line in SKILL.md |
| structure met, coverage below `current` - 0.02 | read what the form crowds out before merging |
| structure not met | report the checker's misses; no merge |
| guard missed | read the traces; no merge |
