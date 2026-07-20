"""
Competitor & Content Gap: Tier-A competitor keyword overlap/gap, keyword
cannibalization check, and content-gap identification.
"""


def competitor_overlap(keyword, competitor_keywords):
    """Returns the competitor-gap record for this keyword, or None."""
    return competitor_keywords.get(keyword)


def is_content_gap_candidate(keyword_entry):
    """A genuine content-gap opportunity: no mapped page, not spam/DIY/
    job-seeker, and not already flagged High compliance risk (those belong
    on the Avoid List / Compliance flag, not a page-building opportunity)."""
    if keyword_entry["mappedPageId"] is not None:
        return False
    if keyword_entry["intent"] == "Low-Quality":
        return False
    if keyword_entry["complianceRisk"] == "High":
        return False
    if keyword_entry.get("competitorGap"):
        return False
    return True


def detect_cannibalization(entries):
    """Flags pages that have 2+ keywords sharing the same Semrush parentTopic
    mapped to them -- a signal that multiple pages (or multiple keywords
    within the priority list) may be competing for the same search intent."""
    by_page_topic = {}
    for e in entries:
        page = e.get("mappedPageId")
        topic = e.get("parentTopic")
        if not page or not topic:
            continue
        by_page_topic.setdefault((page, topic), []).append(e["keyword"])

    flagged_keywords = set()
    for (_page, _topic), keywords in by_page_topic.items():
        if len(keywords) > 1:
            flagged_keywords.update(keywords)
    return flagged_keywords
