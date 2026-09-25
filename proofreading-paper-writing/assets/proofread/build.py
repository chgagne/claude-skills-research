"""Compile the markup and accept-all builds; bisect by level when markup fails."""
import copy, os, re, shutil, subprocess
from dataclasses import dataclass
from .apply import apply_ledger
from .ledger import LEVELS

_CHANGES_OPTS = re.compile(r"\\usepackage\[[^\]]*\]\{changes\}")
FINAL_LINE = r"\usepackage[final,commandnameprefix=always]{changes}"
BISECT = [set(LEVELS), {"mechanics", "style"}, {"mechanics"}, set()]


@dataclass
class BuildResult:
    ok: bool
    log_tail: str = ""
    pdf: str = None


def latexmk_available():
    return shutil.which("latexmk") is not None


def toggle_final(tex):
    return _CHANGES_OPTS.sub(lambda m: FINAL_LINE, tex, count=1)


def compile_pdf(tex_path, outdir, timeout=600):
    os.makedirs(outdir, exist_ok=True)
    cwd = os.path.dirname(os.path.abspath(tex_path))
    cmd = ["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", "-f-",
           f"-outdir={os.path.abspath(outdir)}", os.path.basename(tex_path)]
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        return BuildResult(False, str(exc))
    job = os.path.splitext(os.path.basename(tex_path))[0]
    pdf = os.path.join(outdir, job + ".pdf")
    log = os.path.join(outdir, job + ".log")
    tail = ""
    if os.path.exists(log):
        with open(log, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
        keep = set()
        for i, l in enumerate(lines):
            if l.startswith("!") or "Emergency stop" in l:
                keep.update((i, i + 1, i + 2))
        errs = [lines[i] for i in sorted(keep) if i < len(lines)]
        tail = "\n".join((errs or lines)[-40:])
    ok = r.returncode == 0 and os.path.exists(pdf)
    return BuildResult(ok, tail, pdf if ok else None)


def _write(paper_dir, name, text):
    p = os.path.join(paper_dir, name)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)
    return p


def render_with_bisect(base_tex, rows, paper_dir, out_name, scratch):
    """Apply rows level-set by level-set until the markup build passes.

    Rows dropped by the bisect are reset to status 'kept' with no cut_reason, so the
    report can say they were never attempted rather than that they failed.
    """
    builds = {"markup": None, "final": None}
    dropped = []
    snapshot = copy.deepcopy(rows)
    for levels in BISECT:
        for r, s in zip(rows, snapshot):
            r.status, r.cut_reason = s.status, s.cut_reason
        applied = apply_ledger(base_tex, rows, levels=levels)
        path = _write(paper_dir, out_name, applied.tex)
        res = compile_pdf(path, os.path.join(scratch, "markup"))
        if res.ok:
            builds["markup"] = True
            dropped = sorted(set(LEVELS) - levels, key=LEVELS.index)
            final_path = _write(paper_dir, out_name.replace(".tex", "-final.tex"), toggle_final(applied.tex))
            fres = compile_pdf(final_path, os.path.join(scratch, "final"))
            builds["final"] = fres.ok
            builds["final_log"] = fres.log_tail
            os.remove(final_path)
            return applied.tex, builds, dropped
        builds["markup_log"] = res.log_tail
    builds["markup"] = False
    return base_tex, builds, list(LEVELS)
