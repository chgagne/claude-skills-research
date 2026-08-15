"""Cross-reference graph and claim-level dependency cycles. Stdlib only.

A proof of Lemma 3 leaning on Theorem 1 whose proof leans on Lemma 3 is circular,
and the paper is wrong. It is one of the very few CRITICALs reachable without any
computer algebra, so it is worth being exact about.

Exactness cuts both ways. A **forward** reference -- a proof citing a lemma stated
later -- is legal LaTeX and completely ordinary practice, so it is recorded and
reported as information, never as a defect. And only references between *claims*
form the dependency graph: a proof citing equation (3) depends on an equation,
not on a theorem, and treating it as a claim edge invents cycles.
"""
import re

from .tokenize import blank_comments, find_env_spans

_LABEL = re.compile(r"\\label\s*\{([^}]*)\}")
_REF = re.compile(r"\\(ref|eqref|cref|Cref|autoref|Autoref|pageref|nameref)"
                  r"\s*\*?\s*\{([^}]*)\}")
_SECTION = re.compile(r"\\(?:sub)*(?:section|paragraph|chapter)\*?\s*"
                      r"(?:\[[^\]]*\])?\s*\{[^}]*\}")

_EQ_ENVS = ("equation", "align", "aligned", "gather", "multline", "eqnarray",
            "split", "flalign", "alignat", "displaymath", "IEEEeqnarray")


def _label_kind(text, pos, claims, eq_spans):
    for c in claims or []:
        if c.source["start"] <= pos < c.source["end"]:
            return "theorem", c.id
    for a, b in eq_spans:
        if a <= pos < b:
            return "equation", None
    tail = text[:pos]
    m = None
    for m in _SECTION.finditer(tail):
        pass
    if m and pos - m.end() < 40:
        return "section", None
    return "unknown", None


def build_refs(text, claims=None, proofs=None, steps=None):
    """The `\\label`/`\\ref` graph, plus claim-level cycles."""
    scan = blank_comments(text or "")
    eq_spans = []
    for nm in _EQ_ENVS:
        for s in find_env_spans(scan, [nm], scan=scan) + \
                 find_env_spans(scan, [nm + "*"], scan=scan):
            eq_spans.append((s.start, s.end))

    labels = {}
    for m in _LABEL.finditer(scan):
        name = m.group(1).strip()
        kind, target = _label_kind(scan, m.start(), claims, eq_spans)
        labels[name] = {"kind": kind, "target": target,
                        "defined_in": {"start": m.start(), "end": m.end()}}

    edges, dangling, forward = [], [], []
    for pr in proofs or []:
        a, b = pr.source["start"], pr.source["end"]
        for m in _REF.finditer(scan[a:b]):
            cmd = m.group(1)
            for raw in m.group(2).split(","):
                lab = raw.strip()
                if not lab:
                    continue
                pos = a + m.start()
                if lab not in labels:
                    dangling.append({"from": pr.id, "label": lab, "cmd": cmd})
                    continue
                edges.append({"from": pr.id, "claim": pr.claim_id, "label": lab,
                              "cmd": cmd, "resolved": True})
                if labels[lab]["defined_in"]["start"] > pos:
                    forward.append({"from": pr.id, "label": lab})

    used = {e["label"] for e in edges}
    for m in _REF.finditer(scan):
        for raw in m.group(2).split(","):
            if raw.strip():
                used.add(raw.strip())
    unused = sorted(l for l in labels if l not in used)

    return {"labels": labels, "edges": edges, "dangling": dangling,
            "unused_labels": unused, "forward_refs": forward,
            "cycles": _cycles(edges, labels)}


def _cycles(edges, labels):
    """Cycles in the claim-depends-on-claim graph.

    Only edges whose target label names a *claim* participate. An equation
    reference is a dependency on a formula, not on a theorem, and counting it
    manufactures cycles that are not there.
    """
    graph = {}
    for e in edges:
        src = e["claim"]
        tgt = labels.get(e["label"], {}).get("target")
        if not src or not tgt:
            continue
        if src == tgt:
            # A proof referring to its own theorem. Measured on arXiv:1806.07572,
            # where this produced a CRITICAL against ordinary writing: nothing
            # distinguishes "by Theorem 1, which we are proving" from "recall the
            # hypotheses of Theorem 1", and the second is what proofs actually do.
            continue
        graph.setdefault(src, set()).add(tgt)

    out, state, stack = [], {}, []

    def visit(node):
        state[node] = 1
        stack.append(node)
        for nxt in sorted(graph.get(node, ())):
            if state.get(nxt) == 1:
                out.append(stack[stack.index(nxt):] + [nxt])
            elif state.get(nxt) is None:
                visit(nxt)
        stack.pop()
        state[node] = 2

    for node in sorted(graph):
        if state.get(node) is None:
            visit(node)
    return out
