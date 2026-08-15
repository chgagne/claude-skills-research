"""Static guard, subprocess execution, and external-checker probing. Stdlib only.

**This is not a security boundary against a hostile adversary**, and the SKILL
says so in as many words. It is a guard against three things that happen without
malice: a model writing `os.system` into a generated script, a script reaching
into the paper directory it was told never to touch, and a `simplify()` that
never returns.

The harness never imports SymPy or Z3. It writes text and runs
`subprocess.run([sys.executable, script])`, which is what keeps
`test_stdlib_only.py` honest and what lets a broken checker install fail without
taking the run down with it.

Every failure path lands on `unverified`. A timeout, a rejected script, a crash, a
missing checker -- none of them may ever become `refuted`. A tool that reports a
counterexample because its own subprocess died has invented a finding, and one of
those is enough to make every later finding unreadable.
"""
import ast
import json
import os
import subprocess
import sys

try:
    import resource
except ImportError:                                   # pragma: no cover - non-POSIX
    resource = None

#: Modules a generated check script may import. Anything else is rejected by name.
ALLOWED_IMPORTS = frozenset((
    "sympy", "z3", "math", "cmath", "fractions", "decimal", "itertools",
    "functools", "operator", "json", "sys", "random", "statistics",
    # Used by the inlined rational harness to seed sampling deterministically.
    "hashlib"))

#: Names whose mere appearance rejects the script.
FORBIDDEN_NAMES = frozenset((
    "open", "exec", "eval", "compile", "__import__", "globals", "locals",
    "vars", "input", "breakpoint", "memoryview"))

DEFAULT_TIMEOUT = 10
MEMORY_LIMIT_BYTES = 2 * 1024 * 1024 * 1024
FILE_LIMIT_BYTES = 16 * 1024 * 1024

INSTALL_HINTS = {
    "sympy": "SymPy is not installed. Ask the user before installing "
             "(`pip install sympy`); do not install it yourself.",
    "z3": "Z3 is not installed. Ask the user before installing "
          "(`pip install z3-solver`); do not install it yourself.",
}


class Checker:
    __slots__ = ("name", "available", "version", "install_hint")

    def __init__(self, name, available, version, install_hint):
        self.name = name
        self.available = available
        self.version = version
        self.install_hint = install_hint

    def as_dict(self):
        return {"name": self.name, "available": self.available,
                "version": self.version}

    def __repr__(self):
        return "Checker(%r, %s, %s)" % (self.name, self.available, self.version)


def probe(name, timeout=20):
    """Is an external checker importable, and at what version?

    Runs in a subprocess on purpose. Importing it here would put a third-party
    module in the harness's own process -- defeating the stdlib guard -- and a
    half-installed package would raise on import and kill the run.
    """
    code = ("import %s as _m, sys; "
            "sys.stdout.write(getattr(_m, '__version__', 'unknown'))" % name)
    try:
        r = subprocess.run([sys.executable, "-c", code], capture_output=True,
                           timeout=timeout, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return Checker(name, False, None, INSTALL_HINTS.get(
            name, "%s is not available. Ask the user before installing it." % name))
    if r.returncode == 0:
        return Checker(name, True, r.stdout.decode("utf-8", "replace").strip(), None)
    return Checker(name, False, None, INSTALL_HINTS.get(
        name, "%s is not available. Ask the user before installing it." % name))


def guard(source):
    """Reasons to refuse to execute `source`. Empty means it may run."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return ["syntax error at line %s: %s" % (exc.lineno, exc.msg)]

    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                root = a.name.split(".")[0]
                if root not in ALLOWED_IMPORTS:
                    bad.append("imports %s" % root)
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root not in ALLOWED_IMPORTS:
                bad.append("imports %s" % (root or "a relative module"))
        elif isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            bad.append("uses %s" % node.id)
        elif isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            bad.append("reaches for %s" % node.attr)
    seen, out = set(), []
    for b in bad:
        if b not in seen:
            seen.add(b)
            out.append(b)
    return out


def _limits(timeout):                                  # pragma: no cover - child
    if resource is None:
        return
    for what, limit in ((getattr(resource, "RLIMIT_AS", None), MEMORY_LIMIT_BYTES),
                        (getattr(resource, "RLIMIT_CPU", None), timeout + 2),
                        (getattr(resource, "RLIMIT_FSIZE", None), FILE_LIMIT_BYTES)):
        if what is not None:
            try:
                resource.setrlimit(what, (limit, limit))
            except (ValueError, OSError):
                pass


def _unverified(detail, **extra):
    out = {"outcome": "unverified", "detail": detail}
    out.update(extra)
    return out


def run_script(path, timeout=DEFAULT_TIMEOUT, env=None):
    """Guard, then execute, then parse one JSON verdict from stdout.

    Never raises, and never returns `refuted` for a harness-side failure.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            source = fh.read()
    except OSError as exc:
        return _unverified("script unreadable: %s" % exc)

    reasons = guard(source)
    if reasons:
        return _unverified("script rejected: %s" % "; ".join(reasons),
                           rejected=reasons)

    child_env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                 "PYTHONHASHSEED": "0", "OPENBLAS_NUM_THREADS": "1",
                 "OMP_NUM_THREADS": "1", "MPLBACKEND": "Agg",
                 "HOME": os.path.dirname(os.path.abspath(path))}
    child_env.update(env or {})

    kwargs = {}
    if resource is not None and os.name == "posix":
        kwargs["preexec_fn"] = lambda: _limits(timeout)
    try:
        r = subprocess.run(
            [sys.executable, os.path.basename(path)],
            cwd=os.path.dirname(os.path.abspath(path)),
            capture_output=True, timeout=timeout,
            stdin=subprocess.DEVNULL, env=child_env, **kwargs)
    except subprocess.TimeoutExpired:
        return _unverified("timeout after %ss" % timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        return _unverified("could not run script: %s" % exc)

    out = r.stdout.decode("utf-8", "replace").strip()
    if not out:
        err = r.stderr.decode("utf-8", "replace").strip().splitlines()
        return _unverified("script produced no verdict%s"
                           % (": " + err[-1] if err else ""))
    for line in reversed(out.splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            data = json.loads(line)
        except ValueError:
            continue
        if isinstance(data, dict) and "outcome" in data:
            return data
    return _unverified("script produced no parsable verdict")
