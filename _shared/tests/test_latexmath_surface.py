"""Ledger assembly, schema surface, and content hashing.

`content_hash` is what lets an explanation written weeks later be refused rather
than silently attached to a step that has since changed. It must survive
reflowing the source and must not survive changing a symbol.
"""
import unittest, sys, pathlib, tempfile, os, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from latexmath import ledger as L  # noqa: E402

PAPER = r"""
\documentclass{article}
\newtheorem{thm}{Theorem}
\newtheorem{lem}[thm]{Lemma}
\newcommand{\R}{\mathbb{R}}
\begin{document}

\begin{lem}\label{lem:pos}
Let $u > 0$. Then $\log u$ is defined.
\end{lem}
\begin{proof}
By definition of the logarithm on $\R_{>0}$, the claim is immediate.
\end{proof}

\begin{thm}\label{thm:main}
Let $\gamma \in [0,1)$. Then $\sum_{t=0}^\infty \gamma^t = \frac{1}{1-\gamma}$.
\end{thm}
\begin{proof}
Write $S = \sum_{t=0}^\infty \gamma^t$. By \ref{lem:pos} and rearranging,
\begin{align}
  S &= 1 + \gamma S \label{eq:fix} \\
    &= \frac{1}{1-\gamma}.
\end{align}
This completes the proof.
\end{proof}

\end{document}
"""


def build(text=PAPER):
    d = tempfile.mkdtemp()
    p = os.path.join(d, "main.tex")
    with open(p, "w") as fh:
        fh.write(text)
    return L.build_ledger(p)


class TestSurface(unittest.TestCase):
    def test_module_surface_is_pinned(self):
        for name in ("build_ledger", "validate", "content_hash", "SCHEMA"):
            self.assertTrue(hasattr(L, name), "missing %s" % name)

    def test_schema_file_ships_and_parses(self):
        p = pathlib.Path(L.__file__).parent / "schema.json"
        self.assertTrue(p.exists(), "schema.json must ship with the module")
        json.loads(p.read_text())

    def test_top_level_keys(self):
        led = build()
        for key in ("schema", "source", "macros", "theorem_envs", "claims",
                    "proofs", "steps", "equations", "refs", "symbols",
                    "coverage", "diagnostics"):
            self.assertIn(key, led)
        self.assertEqual(led["schema"], L.SCHEMA)

    def test_the_ledger_is_json_serialisable(self):
        json.dumps(build())


class TestContent(unittest.TestCase):
    def test_claims_and_proofs_are_found(self):
        led = build()
        self.assertEqual(sorted(c["id"] for c in led["claims"]),
                         ["claim/lem:pos", "claim/thm:main"])
        self.assertEqual(len(led["proofs"]), 2)

    def test_macros_are_expanded_before_anything_reads_the_math(self):
        led = build()
        blob = json.dumps(led)
        self.assertNotIn(r"\\R_", blob, "user macro survived into the ledger")

    def test_steps_carry_their_proof_and_ordinal(self):
        led = build()
        main = [s for s in led["steps"] if s["proof_id"] == "proof/thm:main"]
        self.assertTrue(main)
        self.assertEqual([s["ordinal"] for s in main], sorted(s["ordinal"] for s in main))

    def test_side_conditions_reach_the_step(self):
        led = build()
        kinds = {c["kind"] for s in led["steps"] for c in s["side_conditions"]}
        self.assertIn("nonzero-denominator", kinds)

    def test_a_declared_domain_reaches_the_symbol_table(self):
        led = build()
        by = {s["symbol"]: s for s in led["symbols"]}
        self.assertEqual(by[r"\gamma"]["domain_hint"], "unit-interval-half-open")
        self.assertEqual(by[r"\gamma"]["domain_provenance"], "declared")

    def test_the_reference_graph_resolves(self):
        led = build()
        self.assertEqual(led["refs"]["dangling"], [])
        self.assertIn("lem:pos", [e["label"] for e in led["refs"]["edges"]])

    def test_equations_are_recorded_with_their_rows(self):
        led = build()
        self.assertTrue(led["equations"])
        self.assertTrue(any(e["env"] == "align" for e in led["equations"]))


class TestCoverage(unittest.TestCase):
    def test_coverage_counts_are_consistent(self):
        cov = build()["coverage"]
        self.assertEqual(cov["steps"], sum(cov["steps_by_kind"].values()))
        self.assertEqual(
            cov["steps"],
            cov["checkable_candidates"] + cov["opaque"] + cov["structural"])

    def test_captured_percentage_is_reported(self):
        cov = build()["coverage"]
        self.assertGreater(cov["proof_text_captured_pct"], 90.0)

    def test_opacity_histogram_uses_the_controlled_vocabulary(self):
        led = build(PAPER.replace(
            r"This completes the proof.",
            r"The error is $O(\epsilon)$ with probability at least $1-\delta$. "
            r"This completes the proof."))
        hist = led["coverage"]["opacity_histogram"]
        for key in hist:
            self.assertIn(key.split(":")[0], L.OPACITY_VOCABULARY,
                          "%r is not in the controlled vocabulary" % key)
        self.assertTrue(hist, "an asymptotic claim must be marked opaque")


class TestOperatorMacros(unittest.TestCase):
    """Measured on arXiv:1509.01240: 54 spurious `undefined-operator` reasons.

    The paper writes `\\DeclareMathOperator{\\E}{\\mathbb{E}}`, which expands to
    `\\operatorname{\\mathbb{E}}`. Reading the argument with `[^}]*` stopped at
    the inner brace and produced the operator name `\\mathbb{E`, which is not a
    name at all -- and it double-counted with the expectation reason that was
    already correct.
    """

    PAPER = PAPER.replace(
        r"\newcommand{\R}{\mathbb{R}}",
        "\\newcommand{\\R}{\\mathbb{R}}\n\\DeclareMathOperator{\\E}{\\mathbb{E}}"
    ).replace(r"Write $S = \sum_{t=0}^\infty \gamma^t$.",
              r"Write $S = \E_{\pi}[\sum_{t=0}^\infty \gamma^t]$.")

    def test_an_expectation_operator_is_not_an_undefined_operator(self):
        led = build(self.PAPER)
        bad = [r for s in led["steps"] for r in s["opacity_reasons"]
               if r.startswith("undefined-operator") and "mathbb" in r]
        self.assertEqual(bad, [])

    def test_a_truly_unknown_operator_is_still_reported(self):
        led = build(PAPER.replace(r"1 + \gamma S",
                                  r"1 + \operatorname{pool}(\gamma) S"))
        reasons = {r for s in led["steps"] for r in s["opacity_reasons"]}
        self.assertIn("undefined-operator:pool", reasons)


class TestContentHash(unittest.TestCase):
    def test_hash_survives_reflow(self):
        a = build()
        b = build(PAPER.replace("  S &= 1 + \\gamma S \\label{eq:fix} \\\\",
                                "  S\n     &= 1 + \\gamma S \\label{eq:fix} \\\\"))
        ha = [s["content_hash"] for s in a["steps"] if s["kind"] == "chain-row"]
        hb = [s["content_hash"] for s in b["steps"] if s["kind"] == "chain-row"]
        self.assertEqual(ha, hb, "whitespace must not change a step's identity")

    def test_hash_changes_when_a_symbol_changes(self):
        a = build()
        b = build(PAPER.replace(r"S &= 1 + \gamma S", r"S &= 1 + \gamma T"))
        ha = {s["content_hash"] for s in a["steps"]}
        hb = {s["content_hash"] for s in b["steps"]}
        self.assertNotEqual(ha, hb)

    def test_every_step_has_one(self):
        for s in build()["steps"]:
            self.assertTrue(s["content_hash"])


class TestValidate(unittest.TestCase):
    def test_a_clean_paper_produces_no_errors(self):
        errs = [d for d in L.validate(build()) if d["severity"] == "error"]
        self.assertEqual(errs, [])

    def test_a_dangling_reference_is_diagnosed(self):
        led = build(PAPER.replace(r"\ref{lem:pos}", r"\ref{lem:ghost}"))
        codes = [d["code"] for d in L.validate(led)]
        self.assertIn("dangling-ref", codes)

    def test_an_orphan_proof_is_diagnosed(self):
        led = build(PAPER.replace(
            r"\begin{document}",
            "\\begin{document}\n\\begin{proof} Orphan. \\end{proof}"))
        codes = [d["code"] for d in L.validate(led)]
        self.assertIn("orphan-proof", codes)


class TestSharedLayerHygiene(unittest.TestCase):
    def test_latexmath_does_not_import_a_consumer_skill(self):
        root = pathlib.Path(L.__file__).parent
        for py in root.glob("*.py"):
            src = py.read_text()
            for skill in ("proofcheck", "explain", "bibcheck", "compare"):
                self.assertNotIn("import %s" % skill, src,
                                 "%s imports a consumer" % py.name)

    def test_scholarly_does_not_import_latexmath(self):
        root = pathlib.Path(L.__file__).parent.parent / "scholarly"
        for py in root.glob("*.py"):
            self.assertNotIn("latexmath", py.read_text(),
                             "%s reaches sideways into latexmath" % py.name)


if __name__ == "__main__":
    unittest.main()
