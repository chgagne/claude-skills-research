"""Extract what a draft already cites and what it claims to contribute.

The gap sweep expands outward from what the paper cites, so the seed set has to
be accurate: a key missed here is a whole branch of the citation graph never
explored, and a phantom key sends the sweep somewhere the paper never went.
"""
import os
import re
import sys
from dataclasses import dataclass, field

_SHARED = os.path.expanduser("~/.claude/skills/_shared")
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

from scholarly.bibtex import parse_bib  # noqa: E402
from scholarly.latex import (strip_comments, tex_sources,  # noqa: F401,E402
                             demath)

# \cite, \citep, \citet, \citeauthor, \parencite, \autocite, with optional args.
_CITE = re.compile(r"\\[a-zA-Z]*cite[a-zA-Z]*\s*(?:\[[^\]]*\]\s*)*\{([^}]*)\}")

_CONTRIB_CUE = re.compile(
    r"(our contributions?|we present|we propose|we introduce|we contribute|"
    r"this paper (?:presents|proposes|introduces))", re.I)

# Numbered or lettered list markers inside a contributions sentence.
_MARKER = re.compile(r"\(\s*[0-9ivx]+\s*\)|^\s*[0-9]+\.\s+", re.I | re.M)

# Words that mark a clause boundary. An n-gram containing one is a sentence
# fragment ("chart code until", "execution succeeds supports"), not a topic.
_CLAUSE = {"until", "unless", "while", "when", "where", "because", "so", "then",
           "supports", "support", "succeeds", "succeed", "fails", "fail",
           "produces", "produce", "yields", "yield", "requires", "require",
           "allows", "allow", "enables", "enable", "combines", "combine",
           "addresses", "address", "validates", "validate", "repairs", "repair",
           "generates", "generate", "uses", "use", "using", "given", "based",
           "such", "both", "each", "than", "into", "over", "under", "after",
           "before", "during", "without", "within", "across", "via"}

_STOP = {"a", "an", "the", "our", "we", "this", "that", "these", "those", "of",
         "for", "and", "or", "to", "in", "on", "with", "by", "from", "is", "are",
         "be", "it", "its", "as", "at", "which", "paper", "present", "presents",
         "presented", "propose", "proposes", "proposed", "introduce", "introduces",
         "introduced", "contribute", "contribution", "contributions", "study",
         "novel", "new", "approach", "method", "conclusion", "conclusions",
         "abstract", "introduction", "discussion", "section", "work", "works",
         "show", "shows", "shown", "demonstrate", "demonstrates"}

# Sectioning commands become sentence boundaries so a heading cannot glue itself
# to the sentence that follows it.
_SECTIONING = re.compile(
    r"\\(?:sub)*(?:section|paragraph|chapter)\*?\s*(?:\[[^\]]*\])?\s*\{[^}]*\}")

_TITLE = re.compile(r"\\title\s*(?:\[[^\]]*\])?\s*\{", re.S)
_ABSTRACT_ENV = re.compile(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", re.S | re.I)
_ABSTRACT_CMD = re.compile(r"\\abstract\s*\{", re.S | re.I)


@dataclass
class Seed:
    title: str = ""
    abstract: str = ""
    cited_keys: set = field(default_factory=set)
    cited_titles: list = field(default_factory=list)
    contributions: list = field(default_factory=list)
    angles: list = field(default_factory=list)


def _cited_keys(text: str) -> set:
    keys = set()
    for group in _CITE.findall(text):
        for k in group.split(","):
            k = k.strip()
            if k:
                keys.add(k)
    return keys


def _despecial(text: str) -> str:
    """Sectioning -> sentence boundary, then drop remaining LaTeX markup."""
    text = _SECTIONING.sub(". ", text)
    text = re.sub(r"\\(?:label|ref|cref|autoref|cite[a-zA-Z]*)\s*(?:\[[^\]]*\])*"
                  r"\{[^}]*\}", " ", text)
    text = re.sub(r"\\begin\{[^}]*\}|\\end\{[^}]*\}", ". ", text)
    text = re.sub(r"\\[a-zA-Z]+\*?\s*(?:\[[^\]]*\])?", " ", text)
    return text.replace("{", " ").replace("}", " ")


def _contributions(text: str) -> list:
    text = _despecial(text)
    out = []
    for sentence in re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", text)):
        if not _CONTRIB_CUE.search(sentence):
            continue
        tail = sentence.split(":", 1)[1] if ":" in sentence else sentence
        parts = [p for p in re.split(r";|" + _MARKER.pattern, tail, flags=re.I) if p]
        for p in parts:
            p = re.sub(r"\\[a-zA-Z]+\s*(\[[^\]]*\])?(\{[^}]*\})?", " ", p)
            p = re.sub(r"\s+", " ", p).strip(" .,;:")
            if len(p.split()) >= 3:
                out.append(p)
    return out


def _phrases(text, sizes=(4, 3, 2)):
    """Contiguous n-grams that do not span a clause boundary."""
    out = []
    tokens = re.findall(r"[A-Za-z][A-Za-z-]+", (text or "").lower())
    runs, cur = [], []
    for w in tokens:
        if w in _CLAUSE:
            if cur:
                runs.append(cur)
            cur = []
        elif w not in _STOP:
            cur.append(w)
        else:
            if cur:
                runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    # Longest phrases first across every run: a 4-gram from the second clause is
    # a better query than a 2-gram from the first.
    for n in sizes:
        for run in runs:
            for i in range(len(run) - n + 1):
                out.append(" ".join(run[i:i + n]))
    return out


def _abstract_concepts(abstract: str) -> list:
    """Abstract phrases ordered by how often they recur.

    An abstract is written to be topically dense, so a phrase it repeats is a
    concept the paper is actually about -- a better query than any single
    sentence fragment.
    """
    phrases = _phrases(abstract, sizes=(3, 2))
    counts = {}
    for ph in phrases:
        counts[ph] = counts.get(ph, 0) + 1
    order = {ph: i for i, ph in enumerate(phrases)}
    return sorted(dict.fromkeys(phrases),
                  key=lambda ph: (-counts[ph], order[ph]))


def _angles(title: str, abstract: str, contributions: list) -> list:
    """Title, then recurring abstract concepts, then contribution phrases.

    Title first because it is the paper's own one-line topic statement; the
    abstract next because it names the concepts a related paper would share.
    """
    angles, seen = [], set()
    for phrase in (_phrases(title)
                   + _abstract_concepts(abstract)
                   + [p for c in contributions for p in _phrases(c)]):
        if phrase not in seen:
            seen.add(phrase)
            angles.append(phrase)
    return angles


def extract(tex_paths, bib_path) -> Seed:
    text = ""
    for p in tex_paths:
        try:
            with open(p, encoding="utf-8", errors="replace") as fh:
                text += strip_comments(fh.read()) + "\n"
        except OSError:
            continue

    keys = _cited_keys(text)

    titles = []
    try:
        with open(bib_path, encoding="utf-8", errors="replace") as fh:
            by_key = {e.key: e for e in parse_bib(fh.read())}
        for k in sorted(keys):
            e = by_key.get(k)
            if e and e.fields.get("title"):
                titles.append(e.fields["title"])
    except OSError:
        pass

    title = ""
    m = _TITLE.search(text)
    if m:
        from scholarly.bibtex import _read_balanced
        raw, _ = _read_balanced(text, m.end() - 1)
        title = re.sub(r"\s+", " ", _despecial(raw)).strip()

    abstract = ""
    m = _ABSTRACT_ENV.search(text)
    if m:
        abstract = m.group(1)
    else:
        m = _ABSTRACT_CMD.search(text)
        if m:
            from scholarly.bibtex import _read_balanced
            abstract, _ = _read_balanced(text, m.end() - 1)
    abstract = re.sub(r"\s+", " ", _despecial(abstract)).strip()

    contributions = _contributions(text)
    return Seed(title=title, abstract=abstract, cited_keys=keys,
                cited_titles=titles, contributions=contributions,
                angles=_angles(title, abstract, contributions))
