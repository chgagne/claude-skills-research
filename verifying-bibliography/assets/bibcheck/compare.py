"""Pure comparison logic over parsed entries and fetched records."""
import re
from dataclasses import dataclass
from .normalize import (norm_title, fold, split_authors, author_diff,
                        family_key, given_initial)
from .sources import is_preprint as _is_preprint


@dataclass
class Finding:
    key: str
    field: str
    in_bib: str
    in_record: str
    source: str
    severity: str


def _pages(v):
    return re.sub(r"[-–—]+", "-", (v or "").strip())


def _usable_volume(v):
    """DBLP stores 'abs/2604.08324' in volume for CoRR/arXiv entries."""
    if not v:
        return None
    v = str(v)
    return None if v.startswith("abs/") else v


_BIB_PREPRINT_VENUE = re.compile(r"arxiv|corr\b|preprint|biorxiv|ssrn", re.I)


def _cites_preprint(entry):
    """True when the .bib entry points at a preprint *instead of* a venue.

    An entry that names its venue and also carries eprint/archivePrefix is the
    desired state -- the preprint is a supplementary reference, not the citation
    -- so the presence of those fields alone is never the trigger.
    """
    f = entry.fields
    venue = (f.get("journal") or f.get("booktitle") or "").strip()
    if venue:
        return bool(_BIB_PREPRINT_VENUE.search(venue))
    # No venue at all: the entry rests on the preprint identity.
    return bool(f.get("eprint") or f.get("archiveprefix")
                or f.get("doi", "").lower().startswith("10.48550/"))


def _has_arxiv_identity(entry):
    f = entry.fields
    return bool(f.get("eprint") or f.get("archiveprefix")
                or f.get("doi", "").lower().startswith("10.48550/")
                or _BIB_PREPRINT_VENUE.search(f.get("journal", "")))


def _strongest(records):
    for r in records:
        if r.strong and r.venue != "__DOI_UNRESOLVED__":
            return r
    return records[0] if records else None


def _name_form_mismatches(bib_names, rec_names):
    """Given-name disagreements among authors whose family names already match.

    Papers routinely carry two authors with the same family name (Hengzhe Zhang
    and Mengjie Zhang), so compare the *set* of given initials per family rather
    than pairing off the first match.
    """
    rec_by_family = {}
    for n in rec_names:
        rec_by_family.setdefault(family_key(n), []).append(n)
    out = []
    for n in bib_names:
        group = rec_by_family.get(family_key(n))
        if not group:
            continue
        bi = given_initial(n)
        initials = {given_initial(r) for r in group}
        if bi and initials and "" not in initials and bi not in initials:
            out.append((n, "/".join(group)))
    return out


def check_entry(entry, records):
    key, et = entry.key, entry.etype
    f = entry.fields

    # SKIP is for non-paper entries only. An @inproceedings with an OpenReview
    # URL is still a paper, and an @misc carrying an arXiv id is a preprint that
    # may well have a published version -- both must go through the ladder.
    if (et in ("misc", "online", "electronic", "unpublished")
            and not _has_arxiv_identity(entry) and not f.get("doi")):
        return [Finding(key, "entry", f.get("url", ""), "", "url", "SKIP")]

    unresolved = [r for r in records if r.venue == "__DOI_UNRESOLVED__"]
    usable = [r for r in records if r.venue != "__DOI_UNRESOLVED__"]

    out = []
    if unresolved:
        out.append(Finding(key, "doi", f.get("doi", ""), "does not resolve",
                           "crossref", "CRITICAL"))
    if not usable:
        if not out:
            out.append(Finding(key, "entry", f.get("title", ""), "no record found",
                               "-", "UNVERIFIED"))
        return out

    rec = _strongest(usable)
    strong = rec.strong

    bt, rt = norm_title(f.get("title", "")), norm_title(rec.title)
    title_mismatch = bool(bt and rt and bt != rt)
    if title_mismatch:
        out.append(Finding(key, "title", f.get("title", ""), rec.title, rec.source,
                           "CRITICAL" if strong else "WEAK"))
        # Under a stable identifier a title mismatch is itself the finding, and
        # the other fields are still worth reporting. Under a title search it
        # means we never identified the work at all -- comparing its year or
        # authors would describe a different paper.
        if not strong:
            return out

    if f.get("author"):
        bib_names = split_authors(f["author"])
        only_bib, only_rec = author_diff(bib_names, rec.authors)
        if only_bib:
            out.append(Finding(key, "author", "+" + ", +".join(only_bib),
                               "-" + ", -".join(only_rec) if only_rec else "",
                               rec.source, "CRITICAL" if strong else "WEAK"))
        elif only_rec:
            out.append(Finding(key, "author", "(missing) " + ", ".join(only_rec),
                               ", ".join(rec.authors), rec.source,
                               "MAJOR" if strong else "WEAK"))
        forms = _name_form_mismatches(bib_names, rec.authors)
        if forms:
            out.append(Finding(key, "author-name-form",
                               "; ".join(b for b, _ in forms),
                               "; ".join(r for _, r in forms),
                               rec.source, "MINOR"))

    # Year is compared only against a record reached by a stable identifier, and
    # only when that record is not a preprint. Indexes routinely carry the
    # preprint year beside the published venue (Semantic Scholar reports DMLR
    # 2022 for a paper published in DMLR in 2024), so a title-search year cannot
    # distinguish a real error from the normal preprint/published gap.
    by = f.get("year", "")
    authoritative = [r for r in usable if r.strong and not _is_preprint(r) and r.year]
    if by.isdigit() and authoritative:
        years = {r.year for r in authoritative}
        by_i = int(by)
        if by_i not in years and not any(abs(by_i - y) <= 1 for y in years):
            severity = "MINOR" if et == "book" else "MAJOR"
            out.append(Finding(key, "year", by, "/".join(str(y) for y in sorted(years)),
                               rec.source, severity))

    # Volume/issue/pages are only compared against a record reached by a stable
    # identifier. A title-search hit may be a different edition, a reprint, or a
    # review of the same work, so its volume and pages say nothing.
    if strong:
        for bib_f, rec_v, label in (("volume", _usable_volume(rec.volume), "volume"),
                                    ("number", rec.issue, "issue")):
            bv = f.get(bib_f, "").strip()
            if bv and rec_v and fold(bv) != fold(str(rec_v)):
                out.append(Finding(key, label, bv, str(rec_v), rec.source, "MAJOR"))

        bp, rp = _pages(f.get("pages", "")), _pages(rec.pages)
        if bp and rp and bp != rp:
            out.append(Finding(key, "pages", bp, rp, rec.source, "MAJOR"))

    # A conference entry whose "volume" is really the publication year is a
    # citation-export artifact (ICLR has no volumes; 'volume={2025}' on a 2025
    # paper is the year leaking into the field). Numbered series are legitimate:
    # Advances in NeurIPS 2022 genuinely is volume 35, so only fire when the
    # volume looks like the year and no record reports a volume of its own.
    bib_vol = f.get("volume", "").strip()
    if (et == "inproceedings" and bib_vol.isdigit() and len(bib_vol) == 4
            and by.isdigit() and abs(int(bib_vol) - int(by)) <= 1
            and not any(_usable_volume(r.volume) for r in usable)):
        out.append(Finding(key, "volume", bib_vol,
                           "looks like the publication year, not a volume; "
                           "no record reports a volume",
                           rec.source, "MINOR"))

    # Venue is only meaningful against a published record: a preprint record
    # always reports its venue as "arXiv", which says nothing about where the
    # work appeared. Compare with punctuation stripped ("Linguistics: ACL 2024"
    # and "Linguistics ACL 2024" are the same venue).
    venue_bib = f.get("journal") or f.get("booktitle") or ""
    if venue_bib and rec.venue and strong and not _is_preprint(rec):
        vb, vr = norm_title(venue_bib), norm_title(rec.venue)
        if vb and vr and vb not in vr and vr not in vb:
            out.append(Finding(key, "venue", venue_bib, rec.venue, rec.source, "MAJOR"))

    # The venue of record outranks the preprint. When the entry cites a preprint
    # and a published record exists, say so -- the preprint may stay in the entry
    # as a supplementary url/eprint, but it must not be the citation itself.
    if _cites_preprint(entry):
        # Claiming "a published version exists" sends the author hunting for it,
        # so it needs identity, not just a plausible hit. The candidate must
        # carry the same title, and come from evidence we trust: an
        # identifier-resolved record, or DBLP (near-complete for CS venues).
        #
        # Both guards earn their place. DBLP answered the InfoNCE preprint with
        # "Self-Supervised EEG Representation Learning with Contrastive
        # Predictive Coding" -- right source, different paper. OpenAlex answers
        # with the right title under an invented venue.
        published = [r for r in usable
                     if not _is_preprint(r) and r.venue
                     and (r.strong or r.source == "dblp")
                     and norm_title(r.title) == bt]
        if published:
            p = published[0]
            where = f"{p.venue}" + (f" ({p.year})" if p.year else "")
            out.append(Finding(key, "preprint",
                               f.get("journal") or f.get("booktitle") or "arXiv preprint",
                               f"published version exists: {where} — cite it, "
                               f"keep the preprint as a supplementary url",
                               p.source, "MINOR"))

    if not out and not strong:
        out.append(Finding(key, "entry", "", "title-search match only",
                           rec.source, "WEAK"))
    return out
