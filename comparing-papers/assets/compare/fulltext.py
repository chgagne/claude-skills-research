"""Acquire the best available text for a paper.

The ladder matters more than it looks. Everything this skill reports comes from
appendices as often as from the body -- training scale, seed counts and compute
budgets are almost never in the abstract -- so settling for an abstract is not a
slightly worse answer, it is a different and much weaker one. Documents that end
up there are marked `degraded` and the report says so.

    1. arXiv e-print source  LaTeX, read with stdlib tarfile/gzip
    2. arXiv PDF             via pdftotext, only if that binary exists
    3. open-access PDF       via OpenAlex oa_url, same caveat
    4. abstract              degraded

Rung 1 leads because LaTeX needs no PDF parsing, keeps section headings exact,
and preserves appendices that PDF extraction routinely mangles.
"""
import gzip
import io
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.parse
from dataclasses import dataclass, field

_SHARED = os.path.expanduser("~/.claude/skills/_shared")
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

from scholarly.latex import split_sections  # noqa: F401,E402
from scholarly.retrieval import (_mailto_param, _HOST_DELAY,  # noqa: E402
                                 get_bytes,
                                 get_json, s2_api_key)

# arXiv asks for 3s between requests; e-print tarballs are large, so be polite
# on the web host as well as the API host.
_HOST_DELAY.setdefault("arxiv.org", 3.0)


@dataclass
class Document:
    sections: list = field(default_factory=list)   # [(heading, body)]
    source: str = ""
    degraded: bool = False

    def text(self):
        return "\n".join(f"{h}\n{b}" for h, b in self.sections)


def _tex_from_eprint(blob):
    """arXiv serves either a tarball or a single gzipped .tex."""
    if not blob:
        return ""
    try:
        with tarfile.open(fileobj=io.BytesIO(blob), mode="r:*") as tf:
            names = [n for n in sorted(tf.getnames()) if n.lower().endswith(".tex")]
            parts = []
            for n in names:
                fh = tf.extractfile(n)
                if fh:
                    parts.append(fh.read().decode("utf-8", "replace"))
            return "\n".join(parts)
    except (tarfile.TarError, EOFError):
        pass
    try:
        return gzip.decompress(blob).decode("utf-8", "replace")
    except (OSError, EOFError):
        return ""


def _pdftotext(blob):
    """Extract text from PDF bytes. Returns None when poppler is not installed."""
    if not blob or not shutil.which("pdftotext"):
        return None
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "p.pdf")
        with open(src, "wb") as fh:
            fh.write(blob)
        try:
            r = subprocess.run(["pdftotext", "-q", src, "-"],
                               capture_output=True, timeout=120)
        except (OSError, subprocess.SubprocessError):
            return None
    text = r.stdout.decode("utf-8", "replace").strip()
    return text or None


def _arxiv_source(ref):
    if not ref.arxiv_id:
        return None
    return get_bytes(f"https://arxiv.org/e-print/{urllib.parse.quote(ref.arxiv_id)}")


def _arxiv_pdf(ref):
    if not ref.arxiv_id:
        return None
    return _pdftotext(get_bytes(
        f"https://arxiv.org/pdf/{urllib.parse.quote(ref.arxiv_id)}"))


def _oa_pdf(ref):
    if not ref.doi:
        return None
    d = get_json(f"https://api.openalex.org/works/doi:{urllib.parse.quote(ref.doi)}"
                 f"{_mailto_param('?')}&select=open_access")
    url = ((d or {}).get("open_access") or {}).get("oa_url")
    if not url:
        return None
    return _pdftotext(get_bytes(url))


def _abstract(ref):
    if not ref.s2_id and not ref.doi and not ref.arxiv_id:
        return None
    ident = (f"DOI:{ref.doi}" if ref.doi
             else f"arXiv:{ref.arxiv_id}" if ref.arxiv_id else ref.s2_id)
    key = s2_api_key()
    d = get_json("https://api.semanticscholar.org/graph/v1/paper/"
                 + urllib.parse.quote(str(ident)) + "?fields=abstract",
                 {"x-api-key": key} if key else None)
    return (d or {}).get("abstract")


def fetch(ref):
    """Best available text for this paper, with the rung recorded."""
    tex = _tex_from_eprint(_arxiv_source(ref))
    if tex.strip():
        return Document(sections=split_sections(tex), source="arxiv-latex")

    for getter, name in ((_arxiv_pdf, "arxiv-pdf"), (_oa_pdf, "oa-pdf")):
        text = getter(ref)
        if text and text.strip():
            return Document(sections=split_sections(text), source=name)

    abstract = _abstract(ref)
    if abstract:
        return Document(sections=[("Abstract", abstract)], source="abstract",
                        degraded=True)
    return Document(sections=[], source="none", degraded=True)
