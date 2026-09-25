# What counts as a writing defect

Four levels. A row must fit exactly one. When a sentence has several defects, one row per
defect, or one `style` row that fixes them all with a rationale naming each.

## mechanics — the sentence is wrong

Agreement, tense slips, missing or wrong articles, wrong preposition, spelling, duplicated
words, punctuation before citations (`text.\citep` → `text \citep{}.`), a space before `~`,
`Fig.` vs `Figure` inconsistency against the paper's own convention, dangling `\ref` forms
(`Tables 2 and 3` where the paper elsewhere writes `Tables~2 and~3`), inconsistent
hyphenation of the same compound, capitalisation of a defined term. Rendered as bare
track changes, no comment, uncapped. Confidence is usually ≥ 0.9; below 0.7 it is not
mechanics, it is style.

## style — the sentence is right but reads badly

Wordiness (`in order to`, `it is worth noting that`), stacked nouns, a passive that hides
the agent where the agent matters, hedges piled on a result the numbers support, an
intensifier where the number should speak (`very large` → `40×`), vague quantifiers
(`most`, `often`, `substantially`) where a number exists in a table, mixed register
(`kind of`, `a lot`), metaphors that do not translate (`the loss falls off a cliff`), long subject
before the verb, a sentence carrying two claims, non-native phrasing the field profile does
not use. **Every style row cites a rule.** Rendered as a track change with a margin tag.
Soft cap: two kept rows per paragraph.

## flow — the paragraph is right but the reader has to work

No topic sentence; evidence before the claim it supports; a transition missing between
two paragraphs that change subject; redundancy with another section (say which); a
paragraph that could be cut without loss; a figure discussed before it is introduced;
a result stated in the intro that the results section words differently. Comment-only,
anchored at the paragraph's first sentence. Soft cap: one per paragraph, 25 per paper
together with framing.

## framing — the paper is right but presents itself wrongly

A term used before it is defined or defined twice differently (from the glossary); two
names for one concept; the contribution list claiming more or less than the results
sections show; abstract, introduction and conclusion disagreeing on what was found; a
limitation acknowledged in one place and contradicted in another; the title or the first
sentence promising a different paper. Comment-only. Same cap as flow.

## Not a defect

British vs American spelling when consistent. First-person plural. A hedge in a
limitations paragraph. Author preferences recorded in `preferences.md`. Any change the
noise gate cannot tie to a rule. Typographic issues visible only in the PDF text layer.

## The noise gate's questions, in order

1. Does the replacement preserve meaning, including every number, citation and hedge that
   was there? If not: `meaning changed`.
2. Which rule does this rest on? None: `taste, not defect`.
3. Does the author profile use exactly this construction as a habit? If yes and the field
   profile does not object: `contradicts author profile`.
4. Is there an earlier row on the same anchor or the same defect? `duplicate of W<m>`.
5. Over cap for this paragraph or the paper? Cut lowest confidence first: `cap`.
