# The writing ledger

One JSON object per line in `writing-ledger.jsonl`. Agents append rows; the noise gate
sets `status`; `render-ledger.py` applies rows with `status: "kept"` and writes the final
statuses back.

| Field | Type | Rule |
|---|---|---|
| `id` | `W<n>` | unique, numbered in order of creation across all agents |
| `level` | `mechanics` \| `style` \| `flow` \| `framing` | see `critique-rubric.md` |
| `section` | string | as printed, e.g. `3.1`, `Abstract`, `A.2` |
| `para` | int | paragraph index within the section, 1-based |
| `anchor` | string | exact tex substring, whole tokens, unique in the file. For `flow`/`framing`: the first sentence of the paragraph |
| `replacement` | string or null | new text for `mechanics`/`style`; `""` means delete; `null` for comment-only rows |
| `comment` | string | margin note, `W<n>: ` prefix, ≤ 15 words after the prefix. May be empty for `mechanics` |
| `rationale` | string | one to three sentences for the report; say what is wrong and why the fix is better |
| `rule` | string | `defaults:<key>` \| `field:<key>` \| `author:<key>` \| `pref:<key>` \| `run:<n>`. Required for `style` |
| `confidence` | 0–1 | the worker's own estimate; the gate cuts lowest first when over cap |
| `status` | `proposed` → `kept`/`cut` → `applied`/`degraded`/`unanchored` | set by the gate, then the renderer |
| `cut_reason` | string or null | gate: `meaning changed`, `taste, not defect`, `contradicts author profile`, `duplicate of W<m>`, `cap`; renderer: `ambiguous anchor (n matches)`, `inside cite|math|tabular|resizebox|footnote|CL-markup`, `not a whole token`, `overlaps W<m>`, `anchor not found` |

Anchor rules the renderer enforces (`assets/proofread/anchors.py`):

- Copy the anchor from the **tex**, not from the PDF. Ligatures, `~`, `\,` and `--` differ.
- Whole tokens: `wether` → `whether`, never `w` → `wh`.
- Include enough context to be unique. If a phrase recurs, extend the anchor to the sentence.
- Never anchor inside `\cite{}`, math, `tabular`, `\resizebox`, `\footnote`, or existing
  `\ch*` markup. Comment on the paragraph instead and put the rewrite in `rationale`.
- Anchors may span a line break; the renderer matches across whitespace.
