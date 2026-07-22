"""
Rule-based "Needs Attention" alert generation. Runs after every other
analysis module has populated a keyword entry, so rules can key off any
field: mappedPageId, complianceRisk, confidence sub-scores, or a position
delta vs the previous refresh (from data/keyword_history_<brand>.json).
"""

CONTENT_GAP_VOLUME_THRESHOLD = 1200
RANK_DROP_THRESHOLD = 3.0


def _alert(severity, category, keyword, text, source):
    return {"severity": severity, "category": category, "keyword": keyword, "text": text, "source": source}


def generate_needs_attention(entries, position_history):
    alerts = []

    for e in entries:
        total_volume = sum(e["coreSearchMetrics"]["volumeByCountry"].values())

        if e["mappedPageId"] is None and e["contentGapCandidate"] and total_volume >= CONTENT_GAP_VOLUME_THRESHOLD:
            alerts.append(_alert(
                "high", "CONTENT GAP", e["keyword"],
                f"“{e['keyword']}” is high-volume ({total_volume:,}/mo across tracked countries) "
                "but no page currently targets it.",
                "Semrush",
            ))

        if e["complianceRisk"] == "High":
            alerts.append(_alert(
                "high", "COMPLIANCE RISK", e["keyword"],
                f"“{e['keyword']}” is flagged for unsubstantiated medical-claim language "
                f"({', '.join(e['complianceFlaggedTerms'])}) -- do not use in ads or landing-page copy as-is.",
                "Compliance Check",
            ))

        history = position_history.get(e["keyword"])
        current_position = e["coreSearchMetrics"]["currentRankingPosition"]
        if history and current_position is not None:
            previous_position = history[-1]["position"]
            delta = current_position - previous_position
            if delta >= RANK_DROP_THRESHOLD:
                alerts.append(_alert(
                    "medium", "RANK DROP", e["keyword"],
                    f"Ranking for “{e['keyword']}” dropped from position {previous_position} to "
                    f"{current_position} since the last refresh.",
                    "GSC",
                ))

        if e["underperformanceFlag"]:
            alerts.append(_alert(
                "medium", "LOW ENGAGEMENT", e["keyword"],
                f"“{e['keyword']}” ranks well (position {current_position}) but GA4 engagement "
                "is poor -- likely a content/page problem, not a visibility problem.",
                "GA4",
            ))

    severity_order = {"high": 0, "medium": 1, "low": 2}
    alerts.sort(key=lambda a: severity_order.get(a["severity"], 3))
    return alerts
