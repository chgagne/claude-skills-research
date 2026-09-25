"""Register statistics of a LaTeX corpus: what a style profile is built on."""
import os, re, statistics, sys
from collections import Counter

_SHARED = os.path.expanduser("~/.claude/skills/_shared")
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)
from scholarly.latex import strip_comments, demath  # noqa: E402

HEDGES = ("may", "might", "could", "suggest", "suggests", "appear", "appears", "seem", "seems",
          "likely", "possibly", "potentially", "arguably", "somewhat", "relatively", "often",
          "generally", "tend", "tends", "roughly", "approximately")
INTENSIFIERS = ("very", "extremely", "significantly", "substantially", "dramatically", "highly",
                "remarkably", "clearly", "obviously", "surprisingly", "interestingly", "notably",
                "strikingly", "crucially", "importantly", "novel", "simple", "elegant")
_ABBREV = ("e.g.", "i.e.", "et al.", "Fig.", "Figs.", "Eq.", "Eqs.", "Sec.", "Secs.", "Tab.", "vs.", "cf.",
           "resp.", "approx.", "Dr.", "Prof.", "No.")
_BE = r"\b(?:is|are|was|were|be|been|being)\b"
_NOT_PARTICIPLE = r"(?!(?:often|even|then|between|seven|eleven|open|golden|oxygen|red|need|indeed|down|own|town|bed|hidden|sudden)\b)"
_ADVERB = r"(?:(?:\w+ly|then|also|often|already|still|now|not|never|first|thus|therefore)\s+)?"
_IRREGULAR = r"done|made|found|kept|held|set|put|left|sent|lost|cut|run|won|read|shown|known|seen|drawn|met|fed|led|built|thought|brought|taught"
_PASSIVE = re.compile(_BE + r"\s+" + _ADVERB + r"(?:" + _NOT_PARTICIPLE + r"\w+(?:ed|en|wn|ught|ilt)|(?:" + _IRREGULAR + r"))\b", re.I)
_FIRST = re.compile(r"\b(?:we|our|ours|us)\b", re.I)
_PAST = re.compile(r"\b(?:was|were|had|did|\w{3,}ed)\b", re.I)
_PRESENT = re.compile(r"\b(?:is|are|has|have|does|do|we\s+\w+(?<!ed)\b)\b", re.I)
_REF_FORMS = ("Figure~\\ref", "Fig.~\\ref", "Figure \\ref", "\\fref", "Table~\\ref", "Tab.~\\ref", "\\tref",
              "Section~\\ref", "Sec.~\\ref", "\\S\\ref", "\\sref", "Equation~\\ref", "Eq.~\\ref", "\\eqref")


def _protect(text):
    for i, a in enumerate(_ABBREV):
        text = text.replace(a, a.replace(".", f"\x00{i}\x00"))
    text = re.sub(r"(\d)\.(\d)", lambda m: m.group(1) + "\x00d\x00" + m.group(2), text)
    return text


def _restore(text):
    for i, a in enumerate(_ABBREV):
        text = text.replace(f"\x00{i}\x00", ".")
    return text.replace("\x00d\x00", ".")


def sentences(text):
    t = _protect(re.sub(r"\s+", " ", text or "").strip())
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\\(\"'])", t)
    return [_restore(p).strip() for p in parts if p.strip()]


def _words(s):
    return re.findall(r"[A-Za-z][A-Za-z'-]*", s)


def passive_rate(sents):
    return sum(1 for s in sents if _PASSIVE.search(s)) / len(sents) if sents else 0.0


def first_person_rate(sents):
    return sum(1 for s in sents if _FIRST.search(s)) / len(sents) if sents else 0.0


def vocab(sents, words):
    c = Counter(w.lower() for s in sents for w in _words(s))
    return {w: c.get(w, 0) for w in words}


def length_quantiles(sents):
    n = sorted(len(_words(s)) for s in sents) or [0]
    q = lambda p: n[min(len(n) - 1, int(p * len(n)))]
    return {"q10": q(0.1), "q50": q(0.5), "q90": q(0.9), "max": n[-1], "mean": round(statistics.fmean(n), 1)}


def tense_by_section(sections):
    out = {}
    for heading, body in sections:
        out[heading] = {"past": len(_PAST.findall(body)), "present": len(_PRESENT.findall(body))}
    return out


def ref_style(text):
    return {f: text.count(f) for f in _REF_FORMS}


def profile(sections, raw_text):
    body = " ".join(b for _, b in sections)
    sents = sentences(body)
    return {"n_sentences": len(sents), "length": length_quantiles(sents),
            "passive_rate": round(passive_rate(sents), 3), "first_person_rate": round(first_person_rate(sents), 3),
            "hedges": vocab(sents, HEDGES), "intensifiers": vocab(sents, INTENSIFIERS),
            "tense": tense_by_section(sections), "refs": ref_style(raw_text),
            "sentences_per_paragraph": _spp(raw_text)}


def _spp(raw_text):
    paras = [len(sentences(p)) for p in re.split(r"\n\s*\n", strip_comments(raw_text)) if len(_words(p)) > 20]
    return round(statistics.fmean(paras), 1) if paras else 0


def to_markdown(prof, title):
    L = prof["length"]
    out = [f"# Register statistics: {title}", "",
           f"- sentences: {prof['n_sentences']}; words per sentence q10/q50/q90 = {L['q10']}/{L['q50']}/{L['q90']}, mean {L['mean']}, max {L['max']}",
           f"- passive-construction rate: {prof['passive_rate']}", f"- first-person rate: {prof['first_person_rate']}",
           f"- sentences per paragraph (mean): {prof['sentences_per_paragraph']}", "",
           "## Hedges (count)", "", ", ".join(f"{w} {n}" for w, n in sorted(prof["hedges"].items(), key=lambda t: -t[1]) if n), "",
           "## Intensifiers (count)", "", ", ".join(f"{w} {n}" for w, n in sorted(prof["intensifiers"].items(), key=lambda t: -t[1]) if n), "",
           "## Tense by section (past / present markers)", ""]
    out += [f"- {h}: {t['past']} / {t['present']}" for h, t in prof["tense"].items()]
    out += ["", "## Cross-reference forms", ""]
    out += [f"- `{f}`: {n}" for f, n in prof["refs"].items() if n]
    return "\n".join(out) + "\n"
