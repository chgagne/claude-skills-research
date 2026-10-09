# The Antidote pass (optional, step 3b)

Antidote (Druide) is a commercial French/English checker for macOS. It has no API: its
AppleScript only opens windows, and its connectors talk over an undocumented socket. So
the pass is a hand-off. The user corrects a copy in Antidote, and `antidote-rows.py`
turns the differences into `mechanics` rows that go through the gate and the renderer
like any other row.

## Why the corrected copy is never used directly

Measured on a French LaTeX file with a dozen planted errors. Antidote fixed every
agreement and accent, but it also silently damaged the source:

| Damage | Effect |
|---|---|
| `94,2\%` became `94,2~%` | `%` now starts a comment. It compiles with no error, and the PDF loses the rest of the line, citation included |
| `préliminaire, ils suggèrent que la` became `préliminaires, il su~he2016deep. La` | a citation key pasted into prose at the wrong offset |
| `référence \cite{…}` became `référence\cite{…}` | space before the citation dropped |
| three source lines merged into one | every diff against collaborators bloats |
| `~:` added before colons | redundant with babel-french |

The script diffs **tokens**: whitespace, `~` and no-break spaces are separators, so
reflow and spacing changes vanish. Each remaining change becomes a row anchored in the
original, or is refused with a reason:

| Refusal | Means |
|---|---|
| `unescaped %` | the copy turned `\%` into `%`; the fix is lost but the original is safe |
| `drops a LaTeX escape or command` / `touches LaTeX markup` | the change reaches into a macro, brace or `$` |
| `copies a citation key or label into prose (garbled)` | a garble; its neighbours are refused too (`next to a garbled span`) |
| `low similarity` / `rewrite, not a mechanics fix` | a rephrasing (`tel que` → `comme`) or a garble; review by hand |
| `inside math` / `inside cite` / … | the renderer could not apply it anyway |
| `duplicate of W<n>` | a section worker already has a row there |

Edits inside LaTeX comments are counted and otherwise ignored.

## Steps

1. Copy the tex the renderer will edit (`main.tex`, or the science-only copy) to
   `antidote.tex`. Never open `main.tex` itself in Antidote.
2. `open -a "$(ls -d /Applications/Antidote/Antidote*.app | tail -1)" antidote.tex`,
   then tell the user: correct, save, say when done. Do this as the section workers
   start, so the human pass overlaps their run.
3. After the workers finish (so their id blocks exist and duplicates are caught):

   ```
   python3 assets/antidote-rows.py --orig main.tex --corrected antidote.tex \
     --ledger writing-ledger.jsonl --review antidote-review.md
   ```

   Rows take the next free block of 100, with `rule: "tool:antidote"` and status
   `proposed`.
4. Read `antidote-review.md`. A refused rephrasing that is a real improvement may become
   a `style` row written by hand, with a rule. Never copy text from `antidote.tex`
   into the paper.
5. Mention the pass in the hand-back: rows appended, refused count, and how many `%`
   escapes the copy lost. The user should know never to paste that copy back.

## Limits

Measured on French only. English correction runs through the same engine but its LaTeX
damage is unmeasured. On plain Markdown the same Antidote pass did no damage (it only
added `\:`/`\.` escapes and no-break spaces), so the copy-and-diff detour is a LaTeX need.
