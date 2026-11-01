"""Every training-budget statement in a paper, converted to examples seen where the text allows.

A paper rarely states its budget once. It gives epochs in one sentence and the epoch size in
another, steps in a hyperparameter table and the batch size in the text, prompts per round and a
number of rounds. A baseline retrained at a fraction of its published scale hides in exactly
that spread, so this module lists every budget it can read, with the arithmetic shown, instead
of picking one.

Same rules as `axes.py`: never invent (a statement it cannot convert stays in its own unit), and
never assert without provenance (every entry keeps its quote and section).
"""
import re
from dataclasses import dataclass, field

_MAG = {"k": 1e3, "thousand": 1e3, "m": 1e6, "million": 1e6, "b": 1e9, "billion": 1e9}
_N = r"(\d[\d,]*(?:\.\d+)?)\s*(k|m|b|thousand|million|billion)?\b"
_ITEMS = (r"samples?|examples?|sequences?|pairs?|images?|prompts?|episodes?|instances?|"
          r"demonstrations?|clips?|videos?|questions?|problems?|utterances?|trajectories|"
          r"documents?|sentences?|items?|replies|responses?|conversations?|tasks?")

_STEPS = re.compile(_N + r"\s*(?:optimi[sz]er\s+|training\s+|gradient\s+|update\s+)?"
                    r"(?:steps?|iterations?|updates?|iters?)\b", re.I)
_BATCH = re.compile(r"(?:global\s+|total\s+|effective\s+)?batch(?:\s*size)?\s*(?:of|=|:|is)?\s*"
                    + _N, re.I)
_BATCHES_OF = re.compile(_N + r"\s*(?:mini-?)?batches\s+of\s+" + _N, re.I)
_EPOCHS = re.compile(_N + r"\s*(?:full\s+|training\s+)?(?:epochs?|passes)\b", re.I)
_COUNT = re.compile(_N + r"\s*(?:[\w-]+\s+){0,3}?(" + _ITEMS + r")\b", re.I)
_PER_EPOCH = re.compile(r"(?:each|one|per|every)\s+epoch\s+(?:contains|consists of|has|of)\s+"
                        + _N + r"\s*(?:[\w-]+\s+){0,2}?(?:" + _ITEMS + r")\b"
                        r"|" + _N + r"\s*(?:[\w-]+\s+){0,2}?(?:" + _ITEMS + r")\s+per\s+epoch",
                        re.I)
_PER_ROUND = re.compile(_N + r"\s*(?:" + _ITEMS + r")\s+(?:per|each|every)\s+(?:round|iteration)",
                        re.I)
_ROUNDS = re.compile(_N + r"\s*(?:rollout\s+|training\s+)?rounds\b", re.I)
_DATASET = re.compile(r"(?:consisting of|containing|contains|comprising|comprises|totall?ing|"
                      r"uses?|using|collect\w*|of)\s+(?:approximately|about|around|roughly|nearly|"
                      r"over|~)?\s*" + _N + r"\s*(?:[\w/-]+\s+){0,3}?(" + _ITEMS + r")\b", re.I)
_DATA_HINT = re.compile(r"\b(?:training data|train(?:ing)? set|dataset|corpus|distillation data|"
                        r"training uses|we collect|fine-?tun\w* data)\b", re.I)
_TOTAL_HINT = re.compile(r"\b(?:seen|in total|in all|total of|overall|over the run)\b", re.I)
_TRAIN_HINT = re.compile(r"\b(?:train|fine-?tun|pre-?train|post-?train|distill|optimi[sz]|"
                         r"learn|update|schedule|recipe|budget|epoch|step|iteration)", re.I)
_NOT_TRAIN = re.compile(r"\b(?:evaluat|test set|testing|inference|benchmark contains|"
                        r"warm-?up|rollouts? per task|trials?|denois\w*|sampling|per block|per chunk|NFE|"
                        r"inference steps?|decoding)\b", re.I)


@dataclass
class Budget:
    unit: str                  # "examples", "epochs", "steps"
    value: float
    arithmetic: str
    quote: str
    section: str
    combined: bool = False     # True when the factors come from different sentences
    tags: list = field(default_factory=list)


def _num(m_num, m_mag):
    try:
        v = float(m_num.replace(",", ""))
    except ValueError:
        return None
    return v * _MAG.get((m_mag or "").lower(), 1)


def _clean(s):
    s = s.replace("{,}", ",").replace("\\,", ",").replace("~", " ")
    s = re.sub(r"\\multicolumn\{\d+\}\{[^{}]*\}\{([^{}]*)\}", r"\1", s)
    s = re.sub(r"\\(?:textbf|textit|emph|mathrm|text)\{([^{}]*)\}", r"\1", s)
    s = re.sub(r"\$([^$]*)\$", r"\1", s)
    s = re.sub(r"\\times", "x", s)
    s = re.sub(r"(\d)\s*\\?%", r"\1 percent", s)
    return s


def _fmt(v):
    for suf, size in (("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if v >= size:
            return f"{v / size:.4g}{suf}"
    return f"{v:g}"


def _sentences(body):
    captions = re.findall(r"\\caption\{((?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*)\}", body)
    body = re.sub(r"\\begin\{(?:table|tabular)\*?\}.*?\\end\{(?:table|tabular)\*?\}", " ", body,
                  flags=re.S)
    body = body + "\n" + "\n".join(c.strip() + ("" if c.strip().endswith(".") else ".") for c in captions)
    return [s.strip() for s in re.split(r"(?<=[.;!?])\s+(?=[A-Z\\])", body) if s.strip()]


def _table_rows(body):
    for tab in re.findall(r"\\begin\{tabular\*?\}.*?\\end\{tabular\*?\}", body, flags=re.S):
        for row in re.split(r"\\\\", tab):
            cells = [c.strip() for c in row.split("&")]
            if len(cells) >= 2:
                yield cells


def _first(rx, s):
    m = rx.search(s)
    return (_num(m.group(1), m.group(2)), m) if m else (None, None)


def _from_sentence(sent, heading):
    """Budgets stated within one sentence."""
    s = _clean(sent)
    ctx_head = _clean(heading or "")
    if not (_TRAIN_HINT.search(s) or _TRAIN_HINT.search(ctx_head)) or len(s) > 900:
        return []
    out = []
    steps, ms = _first(_STEPS, s)
    batch, mb = _first(_BATCH, s)
    epochs, me = _first(_EPOCHS, s)
    m_bo = _BATCHES_OF.search(s)
    if m_bo:
        nb, b = _num(m_bo.group(1), m_bo.group(2)), _num(m_bo.group(3), m_bo.group(4))
        if nb and b:
            out.append(Budget("examples", nb * b, f"{_fmt(nb)} batches x {_fmt(b)}", sent, heading))
    if steps and batch and not _NOT_TRAIN.search(s[max(0, ms.start() - 40):ms.end() + 10]):
        out.append(Budget("examples", steps * batch, f"{_fmt(steps)} steps x batch {_fmt(batch)}",
                          sent, heading))
    elif steps and not _NOT_TRAIN.search(s[max(0, ms.start() - 40):ms.end() + 10]):
        out.append(Budget("steps", steps, f"{_fmt(steps)} steps", sent, heading))
    m_pr, m_r = _PER_ROUND.search(s), _ROUNDS.search(s)
    if m_pr and m_r:
        per, r = _num(m_pr.group(1), m_pr.group(2)), _num(m_r.group(1), m_r.group(2))
        if per and r:
            out.append(Budget("examples", per * r, f"{_fmt(per)} per round x {_fmt(r)} rounds",
                              sent, heading))
    counts = [(m, _num(m.group(1), m.group(2))) for m in _COUNT.finditer(s)]
    counts = [(m, v) for m, v in counts if v and v >= 10 and not _PER_EPOCH.search(m.group(0))]
    if epochs:
        size = next((v for m, v in counts if abs(m.start() - me.start()) < 160), None)
        pe, _ = _first(_PER_EPOCH, s)
        size = pe or size
        if size:
            out.append(Budget("examples", epochs * size, f"{_fmt(epochs)} epochs x {_fmt(size)}",
                              sent, heading))
        else:
            out.append(Budget("epochs", epochs, f"{_fmt(epochs)} epochs", sent, heading))
    if (_DATA_HINT.search(s) or _DATA_HINT.search(ctx_head)) and not epochs and not steps:
        for m in _DATASET.finditer(s):
            v = _num(m.group(1), m.group(2))
            if v and v >= 10 and not _NOT_TRAIN.search(s[max(0, m.start() - 40):m.end() + 20]):
                out.append(Budget("examples", v, f"{_fmt(v)} {m.group(3).lower()} (dataset, one pass)",
                                  sent, heading, tags=["dataset"]))
                break
    if not out:
        for m, v in counts:
            ctx = s[max(0, m.start() - 60):m.end() + 60]
            if _TOTAL_HINT.search(ctx) or re.search(r"(?:train\w*|tun\w*|distill\w*)\s+"
                                                    r"(?:[\w-]+\s+){0,4}on\b", ctx, re.I):
                if _NOT_TRAIN.search(ctx):
                    continue
                out.append(Budget("examples", v, f"{_fmt(v)} {m.group(3).lower()} (stated)",
                                  sent, heading, tags=["stated"]))
                break
    return out


def _from_tables(body, heading):
    """Hyperparameter tables: 'Training steps & 375', 'Batch size & 32', 'Prompts per round & 32'."""
    out = []
    for cells in _table_rows(body):
        key, vals = _clean(cells[0]).lower(), [_clean(c) for c in cells[1:]]
        if "/" in key and vals and "/" in vals[0]:
            k_parts = [k.strip() for k in key.split("/")]
            q = re.search(r"\b(per\s+[\w\s]+|over the run|in total)$", k_parts[-1])
            if q:
                k_parts = [k if q.group(1) in k else f"{k} {q.group(1)}" for k in k_parts]
            v_parts = [v.strip() for v in vals[0].split("/")]
            if len(k_parts) == len(v_parts):
                for k, v in zip(k_parts, v_parts):
                    out.extend(_from_tables_row(k, [v], quote=" & ".join(cells)[:200], heading=heading))
                continue
        out.extend(_from_tables_row(key, vals, quote=" & ".join(cells)[:200], heading=heading))
    return out


def _from_tables_row(key, vals, quote, heading):
    out = []
    if _NOT_TRAIN.search(key) or re.search(r"generation|diffusion steps|length", key):
        return out
    if True:
        num = None
        for v in vals:
            m = re.search(_N, v, re.I)
            if m:
                num = _num(m.group(1), m.group(2))
                break
        if not num:
            return out
        if re.search(r"\b(?:training\s+)?(?:steps|iterations|updates)\b", key) and "warm" not in key:
            out.append(Budget("steps", num, f"{_fmt(num)} steps (table)", quote, heading, tags=["table"]))
        elif re.search(r"\bepochs?\b", key):
            out.append(Budget("epochs", num, f"{_fmt(num)} epochs (table)", quote, heading, tags=["table"]))
        elif re.search(r"\bbatch\b", key):
            out.append(Budget("batch", num, f"batch {_fmt(num)} (table)", quote, heading, tags=["table"]))
        elif re.search(r"\brounds?\b", key) and not re.search(r"per\s+(?:rollout\s+)?round", key):
            out.append(Budget("rounds", num, f"{_fmt(num)} rounds (table)", quote, heading, tags=["table"]))
        elif re.search(r"(?:" + _ITEMS + r")", key):
            if re.search(r"per\s+(?:rollout\s+)?round|per round", key):
                out.append(Budget("per_round", num, f"{_fmt(num)} per round (table)", quote, heading,
                                  tags=["table"]))
            elif re.search(r"over the run|total|in all", key):
                out.append(Budget("examples", num, f"{_fmt(num)} (table, total)", quote, heading,
                                  tags=["table"]))
    return out


def _doc_level(entries, doc_text):
    """Combine factors stated in different sentences: epochs x epoch size, steps x batch,
    per-round x rounds. Marked `combined`, because the pairing is the tool's reading."""
    out = []
    pe = [(_num(m.group(1) or m.group(3), m.group(2) or m.group(4)), m)
          for m in _PER_EPOCH.finditer(_clean(doc_text))]
    pe = [(v, m) for v, m in pe if v]
    batches = [e for e in entries if e.unit == "batch"]
    if not batches:
        batches = [Budget("batch", v, "", m.group(0), "") for v, m in
                   ((_num(m.group(1), m.group(2)), m) for m in _BATCH.finditer(_clean(doc_text)))
                   if v and v >= 2][:1]
    rounds = [e for e in entries if e.unit == "rounds"]
    datasets = [e for e in entries if "dataset" in e.tags]
    for e in entries:
        if e.unit == "epochs" and pe:
            size = pe[0][0]
            out.append(Budget("examples", e.value * size,
                              f"{_fmt(e.value)} epochs x {_fmt(size)} per epoch ({pe[0][1].group(0).strip()})",
                              e.quote, e.section, combined=True))
        if e.unit == "epochs" and not pe and datasets:
            ds = datasets[0]
            out.append(Budget("examples", e.value * ds.value,
                              f"{_fmt(e.value)} epochs x {_fmt(ds.value)} (dataset: {ds.quote.strip()[:60]})",
                              e.quote, e.section, combined=True))
        if e.unit == "steps" and batches:
            b = batches[0]
            out.append(Budget("examples", e.value * b.value,
                              f"{_fmt(e.value)} steps x batch {_fmt(b.value)} ({b.quote.strip()[:60]})",
                              e.quote, e.section, combined=True))
        if e.unit == "per_round" and rounds:
            r = rounds[0]
            out.append(Budget("examples", e.value * r.value,
                              f"{_fmt(e.value)} per round x {_fmt(r.value)} rounds",
                              e.quote, e.section, combined=True))
    return out


def find_budgets(doc, limit=40):
    """[Budget] for one Document (sections of (heading, body))."""
    entries = []
    for heading, body in doc.sections:
        for sent in _sentences(body):
            entries.extend(_from_sentence(sent, heading))
        entries.extend(_from_tables(body, heading))
    entries.extend(_doc_level(entries, "\n".join(b for _, b in doc.sections)))
    seen, out = set(), []
    for e in entries:
        if e.unit in ("batch", "rounds", "per_round"):
            continue
        k = (e.unit, round(e.value), e.quote[:80])
        if k not in seen:
            seen.add(k)
            out.append(e)
    return out[:limit]


def ratios(draft, other, low=0.5):
    """Pairs of comparable entries (same unit) whose ratio draft/other is at most `low` or at
    least 1/`low`, most extreme first. Evidence for the reader, not a verdict."""
    rows = []
    for d in draft:
        for o in other:
            if d.unit != o.unit or not o.value:
                continue
            r = d.value / o.value
            if r <= low or r >= 1 / low:
                rows.append((r, d, o))
    rows.sort(key=lambda t: min(t[0], 1 / t[0]))
    return rows
