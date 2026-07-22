"""
Shared keyword-entry assembly: turns raw per-source signals (Semrush +
optionally GSC/GA4/Ads + competitor-gap) into one fully-scored entry using
every analysis module. Used by both the weekly batch orchestrator
(build_keyword_research_dashboard.py) and the live search endpoint
(api/search.py) so the two paths can never drift apart.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from analysis import ai_voice_readiness, competitor_and_gap, compliance, confidence, intent_and_audience  # noqa: E402

HIGH_PRIORITY_CONFIDENCE_FLOOR = 55


def resolve_ga4_entry(phase, keyword, gsc_entry, ga4_data):
    """Sample-phase ga4_engagement_sample.json is keyed by keyword (a Phase-1
    simplification). Live GA4 has no native search-query dimension, so
    fetch_ga4.py's live path is keyed by page id instead -- resolve it via
    the keyword's GSC-derived mapped page. Unmapped keywords get no GA4
    signal either way, which is correct: no page, nothing to attribute.
    Shared by build_keyword_research_dashboard.py and api/search.py so
    both callers resolve GA4 identically."""
    if phase == "live":
        page_id = gsc_entry["page"] if gsc_entry else None
        return ga4_data.get(page_id) if page_id else None
    return ga4_data.get(keyword)


def classify_type_and_placement(keyword, mapped_page_id, is_question):
    word_count = len(keyword.split())
    if is_question:
        kw_type = "Question"
    elif word_count >= 5:
        kw_type = "Long-tail"
    elif word_count <= 3:
        kw_type = "Primary"
    else:
        kw_type = "Secondary"

    if kw_type == "Question":
        placement = "FAQ Schema"
    elif kw_type == "Primary":
        placement = "H1" if mapped_page_id else "Meta Title"
    elif kw_type == "Secondary":
        placement = "H2"
    else:
        placement = "H3" if mapped_page_id else "Meta Description"
    return kw_type, placement


def priority_band(entry):
    """High/Medium/Low -- same definition the batch KPI ("High-Priority
    Keywords Found") uses, just per-row and banded instead of boolean, so
    every keyword (weekly batch or live search) carries one consistent
    Priority value."""
    if entry["spamRisk"] == "Flagged" or entry["intent"] == "Low-Quality" or entry["complianceRisk"] == "High":
        return "Low"
    if entry["audienceFitScore"] == "High" and entry["confidenceScore"] >= HIGH_PRIORITY_CONFIDENCE_FLOOR:
        return "High"
    return "Medium"


def build_entry(keyword, semrush_data, gsc_entry, ga4_entry, ads_entry, competitor_gap,
                 trending_phrases, page_titles, brand):
    volume_by_country = semrush_data.get("volumeByCountry", {})
    cpc = semrush_data.get("cpc")
    difficulty = semrush_data.get("difficulty")
    parent_topic = semrush_data.get("parentTopic")

    mapped_page_id = gsc_entry["page"] if gsc_entry else None
    current_position = gsc_entry["position"] if gsc_entry else None

    question = intent_and_audience.is_question(keyword)
    intent = intent_and_audience.classify_intent(keyword, brand)
    spam_risk = intent_and_audience.spam_risk_flag(keyword, brand)
    medical_specificity = intent_and_audience.specificity_score(keyword, brand)
    audience_fit = intent_and_audience.audience_fit_score(keyword, volume_by_country, cpc, brand)

    ai_voice = ai_voice_readiness.ai_voice_fit(keyword, medical_specificity)
    compliance_result = compliance.compliance_check(keyword, brand)
    confidence_score, confidence_subscores = confidence.compute_confidence(
        gsc_entry, ga4_entry, ads_entry, volume_by_country, difficulty
    )
    underperf = confidence.underperformance_flag(gsc_entry, ga4_entry)

    kw_type, placement = classify_type_and_placement(keyword, mapped_page_id, question)
    answerable = question or ai_voice["answerabilityScore"] >= 50

    entry = {
        "keyword": keyword,
        "type": kw_type,
        "suggestedPlacement": placement,
        "answerable": answerable,
        "intent": intent,
        "aiVoiceSearchFit": ai_voice["fit"],
        "audienceFitScore": audience_fit,
        "spamRisk": spam_risk,
        "complianceRisk": compliance_result["overallRisk"],
        "complianceFlaggedTerms": compliance_result["flaggedTerms"],
        "confidenceScore": confidence_score,
        "mappedPageId": mapped_page_id,
        "mappedPage": page_titles.get(mapped_page_id, "Content Gap") if mapped_page_id else "Content Gap",
        "parentTopic": parent_topic,
        "underperformanceFlag": underperf,
        "competitorGap": competitor_gap,
        "coreSearchMetrics": {
            "volumeByCountry": volume_by_country,
            "competition": difficulty,
            "cpc": cpc,
            "currentRankingPosition": current_position,
            "trendingPhrase": keyword in trending_phrases,
        },
        "audienceFitIntent": {
            "intent": intent,
            "audienceFitScore": audience_fit,
            "spamRiskFlag": spam_risk,
            "medicalSpecificityScore": medical_specificity,
        },
        "aiVoiceReadiness": ai_voice,
        "complianceCheck": compliance_result,
        "crossSourceConfidence": {
            "confidenceScore": confidence_score,
            "subscores": confidence_subscores,
            "underperformanceFlag": underperf,
        },
    }
    entry["contentGapCandidate"] = competitor_and_gap.is_content_gap_candidate(entry)
    entry["competitorContentGap"] = {
        "competitorOverlap": competitor_gap,
        "cannibalizationRisk": False,  # filled in by caller after the full-list cannibalization pass
        "contentGap": entry["mappedPageId"] is None,
    }
    entry["priority"] = priority_band(entry)
    return entry


def enrich_with_cached_signal(entry, cached_entry):
    """Live Search tool only: if the searched keyword already exists in the
    last weekly-committed data/keyword_research_data_<brand>.json snapshot, borrow
    its real GSC/GA4/Ads signal (ranking position, mapped page,
    underperformance, and the three subscores) into a freshly-built
    Semrush-only entry, then recompute the composite confidence/priority so
    they reflect the fuller picture instead of Semrush alone. If there's no
    cached match, `entry` is returned unchanged -- its GSC/GA4/Ads sub-scores
    stay None, which the UI must show as "no data yet", not fabricate."""
    if cached_entry is None:
        return entry

    entry["mappedPageId"] = cached_entry["mappedPageId"]
    entry["mappedPage"] = cached_entry["mappedPage"]
    entry["coreSearchMetrics"]["currentRankingPosition"] = cached_entry["coreSearchMetrics"]["currentRankingPosition"]
    entry["underperformanceFlag"] = cached_entry["underperformanceFlag"]
    entry["crossSourceConfidence"]["underperformanceFlag"] = cached_entry["underperformanceFlag"]

    # suggestedPlacement depends on mappedPageId (e.g. Primary -> H1 once a
    # page is mapped, vs Meta Title when it isn't) -- recompute now that
    # mappedPageId may have just changed above.
    question = intent_and_audience.is_question(entry["keyword"])
    _, entry["suggestedPlacement"] = classify_type_and_placement(entry["keyword"], entry["mappedPageId"], question)

    cached_subs = cached_entry["crossSourceConfidence"]["subscores"]
    merged_subs = dict(entry["crossSourceConfidence"]["subscores"])
    for source in ("gsc", "ga4", "ads"):
        merged_subs[source] = cached_subs.get(source)
    composite = confidence.compute_confidence_from_subscores(merged_subs)

    entry["crossSourceConfidence"]["subscores"] = merged_subs
    entry["crossSourceConfidence"]["confidenceScore"] = composite
    entry["confidenceScore"] = composite
    entry["contentGapCandidate"] = competitor_and_gap.is_content_gap_candidate(entry)
    entry["priority"] = priority_band(entry)
    return entry
