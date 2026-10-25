#!/usr/bin/env python3
"""Compile a Lean certificate and audit it: errors, `sorry`, and the axioms behind every theorem.

    python3 ~/.claude/skills/verifying-proofs/assets/lean-certify.py Witness.lean \
        --project ~/lean/probe

The project is any Lean 4 project with Mathlib built (`lake exe cache get`); it is never created
or modified here, apart from a temporary copy of the file that is removed afterwards. The file is
compiled with `#print axioms` appended for every top-level `theorem` and `lemma`, inside the
namespaces it declares.

A certificate is CLEAN when it compiles without errors, uses no `sorry`, and every theorem depends
only on the three standard axioms. Clean says the proof is correct; it does not say the statement
is the paper's. That comparison, the fidelity list, is yours (reference/lean.md).

Exit codes: 0 clean, 1 not clean, 2 Lean unavailable or bad arguments.
"""
import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

STANDARD = {"propext", "Classical.choice", "Quot.sound"}
_DECL = re.compile(r"^\s*(?:@\[[^\]]*\]\s*)?(?:private\s+|protected\s+)?(theorem|lemma)\s+([^\s:({\[]+)")
_NS = re.compile(r"^\s*namespace\s+(\S+)")
_END = re.compile(r"^\s*end\s+(\S+)")
_AXIOMS = re.compile(r"'([^']+)' depends on axioms: \[([^\]]*)\]")
_NO_AXIOMS = re.compile(r"'([^']+)' does not depend on any axioms")


def theorem_names(src):
    """Fully qualified names of top-level theorems and lemmas, tracking `namespace X ... end X`."""
    stack, out = [], []
    for line in src.splitlines():
        m = _NS.match(line)
        if m:
            stack.extend(m.group(1).split("."))
            continue
        m = _END.match(line)
        if m:
            parts = m.group(1).split(".")
            if stack[-len(parts):] == parts:
                del stack[-len(parts):]
            continue
        m = _DECL.match(line)
        if m:
            name = m.group(2)
            out.append(".".join(stack + [name]) if stack and not name.startswith("_root_.") else name.replace("_root_.", ""))
    return out


def parse_output(out, names):
    """Errors, sorry warnings and per-theorem axioms from Lean's output."""
    axioms = {}
    for n, ax in _AXIOMS.findall(out):
        axioms[n] = sorted(a.strip() for a in ax.split(",") if a.strip())
    for n in _NO_AXIOMS.findall(out):
        axioms[n] = []
    errors = [l for l in out.splitlines() if re.search(r":\d+:\d+: error", l)]
    sorry = "declaration uses 'sorry'" in out or any("sorryAx" in a for v in axioms.values() for a in v)
    missing = [n for n in names if n not in axioms]
    nonstandard = {n: [a for a in v if a not in STANDARD] for n, v in axioms.items()}
    nonstandard = {n: v for n, v in nonstandard.items() if v}
    clean = not errors and not sorry and not missing and not nonstandard and bool(names)
    return {"clean": clean, "errors": errors, "sorry": sorry, "theorems": names,
            "axioms": axioms, "nonstandard": nonstandard, "unchecked": missing}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", help="the .lean certificate")
    ap.add_argument("--project", default=os.environ.get("LEAN_PROJECT"),
                    help="Lean project with Mathlib built (or set LEAN_PROJECT)")
    ap.add_argument("--json", action="store_true", help="print the audit as JSON")
    ap.add_argument("--timeout", type=int, default=900)
    a = ap.parse_args(argv)
    if not a.project:
        print("no --project given and LEAN_PROJECT unset", file=sys.stderr)
        return 2
    project = pathlib.Path(a.project).expanduser().resolve()
    if not (project / "lakefile.toml").exists() and not (project / "lakefile.lean").exists():
        print(f"{project} has no lakefile; not a Lean project", file=sys.stderr)
        return 2
    lake = shutil.which("lake")
    if not lake:
        print("lake not found on PATH; Lean is not installed (ask before installing)", file=sys.stderr)
        return 2
    src = pathlib.Path(a.file).read_text()
    names = theorem_names(src)
    body = src.rstrip("\n") + "\n\n" + "".join(f"#print axioms {n}\n" for n in names)
    fd, tmp = tempfile.mkstemp(prefix="certify_", suffix=".lean", dir=project)
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(body)
        try:
            proc = subprocess.run([lake, "env", "lean", tmp], cwd=project, capture_output=True,
                                  text=True, timeout=a.timeout)
            out = proc.stdout + proc.stderr
        except subprocess.TimeoutExpired:
            out = f"{tmp}:1:0: error: timed out after {a.timeout} s"
    finally:
        pathlib.Path(tmp).unlink(missing_ok=True)
    res = parse_output(out, names)
    if a.json:
        print(json.dumps(res, indent=1))
    else:
        print("CLEAN" if res["clean"] else "NOT CLEAN")
        for k in ("errors", "unchecked"):
            for x in res[k]:
                print(f"  {k[:-1]}: {x}")
        if res["sorry"]:
            print("  uses sorry")
        for n, v in res["nonstandard"].items():
            print(f"  {n}: non-standard axioms {v}")
        for n in names:
            if n in res["axioms"]:
                print(f"  {n}: {res['axioms'][n] or 'no axioms'}")
        if not names:
            print("  no theorem or lemma found to audit")
    return 0 if res["clean"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
