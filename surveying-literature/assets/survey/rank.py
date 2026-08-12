"""Grade candidates by how much they threaten the draft's novelty claim.

The point of a gap report is not "here are 200 topically adjacent papers". It is
"here are the three a reviewer will say you should have cited". Grading is
therefore deliberately conservative: THREAT is reserved for work that is both
topically on the contribution *and* reachable from more than one direction in
the citation graph.
"""
import datetime
import math
import os
import sys

_SHARED = os.path.expanduser("~/.claude/skills/_shared")
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)

from scholarly.textnorm import norm_title  # noqa: E402

THREAT, RELATED, BACKGROUND = "THREAT", "RELATED", "BACKGROUND"
_GRADE_ORDER = {THREAT: 0, RELATED: 1, BACKGROUND: 2}

_RECENT_YEARS = 3
_RECENCY_BONUS = 0.5


def angle_overlap(title, angles):
    """How many contribution phrases appear in this title."""
    t = norm_title(title or "")
    if not t:
        return 0
    return sum(1 for a in angles if norm_title(a) and norm_title(a) in t)


def _impute(known):
    """Neutral stand-in for an unknown citation count: the median of its peers.

    arXiv and DBLP publish no counts. Scoring that absence as zero is not a
    neutral choice -- it actively demotes recent parallel work, which is exactly
    what a gap sweep exists to surface.
    """
    if not known:
        return 0
    ordered = sorted(known)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def _per_year(cites, year, today=None):
    """Citations per year since publication. 40 cites since 2010 is weaker
    evidence of impact than 20 cites since last year."""
    this_year = (today or datetime.date.today()).year
    age = max(1, this_year - (year or this_year) + 1)
    return cites / age


def score(candidate, angles, fallback_cites=0):
    overlap = angle_overlap(candidate.title, angles)
    s = 2.0 * overlap + 1.0 * len(candidate.paths)
    cites = candidate.cited_by_count
    if cites is None:
        cites = fallback_cites
    s += 0.2 * math.log10(1 + max(_per_year(cites, candidate.year), 0))
    if candidate.year and candidate.year >= datetime.date.today().year - _RECENT_YEARS:
        s += _RECENCY_BONUS
    return s


def grade(candidate, angles):
    overlap = angle_overlap(candidate.title, angles)
    multi = len(candidate.paths) >= 2
    if overlap and multi:
        return THREAT
    if overlap or multi:
        return RELATED
    return BACKGROUND


def rank(candidates, seed):
    """Return [(Candidate, score, grade)] sorted by grade, then score desc.

    Grade dominates score on purpose: a heavily-cited survey that is merely
    RELATED must never bury the paper that scooped the contribution.
    """
    angles = list(getattr(seed, "angles", []) or [])
    values = list(candidates.values())
    # Impute unknown counts from the candidates that do report one, so a paper
    # found only through arXiv or DBLP is scored as typical rather than as
    # uncited. With nothing known, every candidate shares the same stand-in and
    # the term simply drops out of the comparison.
    known = [c.cited_by_count for c in values if c.cited_by_count is not None]
    fallback = _impute(known)
    out = [(c, float(score(c, angles, fallback)), grade(c, angles))
           for c in values]
    out.sort(key=lambda item: (_GRADE_ORDER[item[2]], -item[1], item[0].title))
    return out
