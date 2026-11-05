"""Offline tests for check-review-form.py (stdlib only)."""
import importlib.util
import pathlib
import unittest

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("crf", HERE.parent / "check-review-form.py")
crf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(crf)


def good_review():
    rows = "\n".join(f"| {i} | {item} | done | checked X |" for i, item in enumerate(crf.CHECKLIST, 1))
    body = {
        "2. Overall assessment": "**Disqualifying findings:** none\n\n**Recommendation: minor revision.** Fine.",
        "2a. Coverage checklist": "| # | Item | Status | Evidence |\n|---|---|---|---|\n" + rows,
    }
    parts = ["# Review: a paper\n"]
    for h in crf.HEADINGS:
        parts.append(f"## {h}\n\n{body.get(h, 'Text.')}\n")
    return "\n".join(parts)


class CheckReviewForm(unittest.TestCase):
    def test_clean_review_passes(self):
        self.assertEqual(crf.check(good_review()), [])

    def test_missing_heading(self):
        t = good_review().replace("## 6. Figures and tables", "## Figures")
        probs = crf.check(t)
        self.assertTrue(any("6. Figures and tables" in p for p in probs), probs)

    def test_out_of_order(self):
        t = good_review()
        a, b = "## 3. Strengths", "## 4. Major concerns"
        t = t.replace(a, "@@A").replace(b, a).replace("@@A", b)
        self.assertTrue(any("order" in p for p in crf.check(t)))

    def test_extra_level2_heading_is_reported(self):
        t = good_review().replace("## 7. Detailed comments by section", "## Extra\n\nx\n\n## 7. Detailed comments by section")
        self.assertTrue(any("Extra" in p for p in crf.check(t)))

    def test_checklist_row_missing(self):
        t = good_review().replace(f"| 14 | {crf.CHECKLIST[13]} | done | checked X |\n", "")
        t = t.replace(f"| 14 | {crf.CHECKLIST[13]} | done | checked X |", "")
        self.assertTrue(any("row 14" in p for p in crf.check(t)))

    def test_checklist_bad_status_and_empty_evidence(self):
        t = good_review().replace(f"| 3 | {crf.CHECKLIST[2]} | done | checked X |", f"| 3 | {crf.CHECKLIST[2]} | maybe |  |")
        probs = crf.check(t)
        self.assertTrue(any("row 3" in p and "status" in p for p in probs), probs)
        self.assertTrue(any("row 3" in p and "evidence" in p for p in probs), probs)

    def test_recommendation_and_disqualifying_required(self):
        t = good_review().replace("**Recommendation: minor revision.** Fine.", "Looks fine.")
        self.assertTrue(any("Recommendation" in p for p in crf.check(t)))
        t = good_review().replace("**Disqualifying findings:** none", "")
        self.assertTrue(any("isqualifying" in p for p in crf.check(t)))

    def test_two_line_gate_accepted(self):
        t = good_review().replace("**Disqualifying findings:** none",
                                  "**Findings that gate the science:** C1\n**Findings that gate the submission but not the judgement:** K1")
        self.assertEqual(crf.check(t), [])

    def test_empty_section_flagged(self):
        t = good_review().replace("## 5. Bibliography audit\n\nText.", "## 5. Bibliography audit\n\n")
        self.assertTrue(any("5. Bibliography audit" in p and "empty" in p for p in crf.check(t)))

    def test_numbering_variants_tolerated(self):
        t = good_review().replace("## 2a. Coverage checklist", "## 2a Coverage checklist").replace("## 9. Action plan", "## 9. Action Plan")
        self.assertEqual(crf.check(t), [])


if __name__ == "__main__":
    unittest.main()
