"""PDF build. Stdlib only, and it never installs anything.

`latexmk` missing leaves the `.tex` written and reports degraded. Losing the
document because a build tool is absent would discard the expensive part of the
work — the expansion — to preserve the cheap part.

The log is scraped for two things that fail silently and are therefore worse than
an error: a missing glyph, which is *deleted* from the PDF so the sentence reads
as though it was never written, and an overfull box, which is how a step block
runs off the right margin. Both were paid for once already in
`build-review-pdf.sh`.
"""
import os
import re
import shutil
import subprocess

_MISSING_GLYPH = re.compile(r"Missing character: There is no (.+?) in font", re.I)
_OVERFULL = re.compile(r"Overfull \\hbox \(([\d.]+)pt too wide\)")

#: Overfull boxes below this are invisible in practice. Above it, look at the page.
OVERFULL_PT = 5.0


def build_pdf(tex_path, latexmk="latexmk", timeout=180, outdir=None):
    """Compile one derivation. Never raises; reports what went wrong."""
    tex_path = os.path.abspath(tex_path)
    workdir = os.path.dirname(tex_path)
    outdir = outdir or os.path.join(workdir, "build")

    if not shutil.which(latexmk):
        return {"ok": False, "degraded": True, "pdf": None,
                "detail": "%s not found -- ask the user before installing a TeX "
                          "distribution. The .tex has been written and is "
                          "unaffected." % latexmk,
                "warnings": []}

    try:
        r = subprocess.run(
            [latexmk, "-pdf", "-interaction=nonstopmode", "-halt-on-error",
             "-outdir=%s" % outdir, os.path.basename(tex_path)],
            cwd=workdir, capture_output=True, timeout=timeout,
            stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return {"ok": False, "degraded": True, "pdf": None,
                "detail": "latexmk timed out after %ss" % timeout, "warnings": []}
    except (OSError, subprocess.SubprocessError) as exc:
        return {"ok": False, "degraded": True, "pdf": None,
                "detail": "could not run latexmk: %s" % exc, "warnings": []}

    log = _read_log(outdir, tex_path)
    warnings = _scrape(log)
    pdf = os.path.join(outdir, os.path.basename(tex_path)[:-4] + ".pdf")

    if r.returncode != 0 or not os.path.exists(pdf):
        return {"ok": False, "degraded": True, "pdf": None,
                "detail": _first_error(log) or
                          r.stderr.decode("utf-8", "replace")[-400:] or
                          "latexmk failed and produced no PDF",
                "warnings": warnings}
    return {"ok": True, "degraded": bool(warnings), "pdf": pdf,
            "detail": "built %s" % os.path.basename(pdf), "warnings": warnings}


def _read_log(outdir, tex_path):
    log = os.path.join(outdir, os.path.basename(tex_path)[:-4] + ".log")
    try:
        with open(log, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def _first_error(log):
    for line in (log or "").splitlines():
        if line.startswith("! "):
            return line.strip()
    return None


def _scrape(log):
    """Failures that produce a PDF anyway, and are therefore easy to miss."""
    out = []
    missing = sorted({m.group(1) for m in _MISSING_GLYPH.finditer(log or "")})
    if missing:
        out.append("missing glyphs, which are deleted silently so the sentence "
                   "reads as though it was never written: " + ", ".join(missing))
    bad = [float(m.group(1)) for m in _OVERFULL.finditer(log or "")]
    bad = [w for w in bad if w > OVERFULL_PT]
    if bad:
        out.append("%d overfull box%s up to %.0fpt -- render the pages and look "
                   "at them before trusting the layout"
                   % (len(bad), "" if len(bad) == 1 else "es", max(bad)))
    return out
