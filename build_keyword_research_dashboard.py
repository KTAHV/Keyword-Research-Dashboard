"""
Orchestrator: load fetcher output (sample or live) -> merge into one entry
per keyword -> run every analysis module -> compute KPIs + Needs Attention
alerts + history deltas -> write data/keyword_research_data.json +
data/keyword_history.json -> emit the self-contained static
keyword-research-dashboard.html.

Usage:
    python build_keyword_research_dashboard.py            # --phase sample (default)
    python build_keyword_research_dashboard.py --phase live

Follows the same data-flow convention as the sibling Page Quality Dashboard:
fetch -> merge -> score -> bake into static HTML as inline JS consts via
json.dumps(..., separators=(",", ":")). No runtime fetch() -- the HTML is
fully self-contained.
"""
import argparse
import json
import os
from datetime import date, datetime, timezone

import config
from analysis import ai_voice_readiness, competitor_and_gap, compliance, confidence, intent_and_audience, rules
from dashboard_html import render_html
from fetchers import (
    fetch_competitor_keywords,
    fetch_ga4,
    fetch_google_ads_search_terms,
    fetch_google_suggest_proxy,
    fetch_gsc,
    fetch_semrush,
)

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "data")
SAMPLE_DIR = os.path.join(DATA_DIR, "sample")
OUTPUT_JSON = os.path.join(DATA_DIR, "keyword_research_data.json")
HISTORY_JSON = os.path.join(DATA_DIR, "keyword_history.json")
OUTPUT_HTML = os.path.join(ROOT, "keyword-research-dashboard.html")

HIGH_PRIORITY_CONFIDENCE_FLOOR = 55
MAX_POSITION_HISTORY_POINTS = 8


def load_history():
    if os.path.exists(HISTORY_JSON):
        with open(HISTORY_JSON, encoding="utf-8") as f:
            return json.load(f)
    with open(os.path.join(SAMPLE_DIR, "keyword_history_sample.json"), encoding="utf-8") as f:
        return json.load(f)


def page_title_by_id():
    return {p["id"]: p["title"] for p in config.PAGES}


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


def collect_trending_phrases(suggest_proxy_data):
    trending = set()
    for seed_data in suggest_proxy_data.values():
        trending.update(seed_data.get("trending", []))
    return trending


def build_entry(keyword, semrush_data, gsc_data, ga4_data, ads_data, competitor_data,
                 trending_phrases, page_titles):
    volume_by_country = semrush_data.get("volumeByCountry", {})
    cpc = semrush_data.get("cpc")
    difficulty = semrush_data.get("difficulty")
    parent_topic = semrush_data.get("parentTopic")

    gsc_entry = gsc_data.get(keyword)
    ga4_entry = ga4_data.get(keyword)
    ads_entry = ads_data.get(keyword)

    mapped_page_id = gsc_entry["page"] if gsc_entry else None
    current_position = gsc_entry["position"] if gsc_entry else None

    question = intent_and_audience.is_question(keyword)
    intent = intent_and_audience.classify_intent(keyword)
    spam_risk = intent_and_audience.spam_risk_flag(keyword)
    medical_specificity = intent_and_audience.medical_specificity_score(keyword)
    audience_fit = intent_and_audience.audience_fit_score(keyword, volume_by_country, cpc)

    ai_voice = ai_voice_readiness.ai_voice_fit(keyword, medical_specificity)
    compliance_result = compliance.compliance_check(keyword)
    confidence_score, confidence_subscores = confidence.compute_confidence(
        gsc_entry, ga4_entry, ads_entry, volume_by_country, difficulty
    )
    underperf = confidence.underperformance_flag(gsc_entry, ga4_entry)
    competitor_gap = competitor_and_gap.competitor_overlap(keyword, competitor_data)

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
        "cannibalizationRisk": False,  # filled in after full-list pass
        "contentGap": entry["mappedPageId"] is None,
    }
    return entry


def compute_kpis(entries):
    total = len(entries)
    high_priority = sum(
        1 for e in entries
        if e["audienceFitScore"] == "High"
        and e["spamRisk"] == "None"
        and e["complianceRisk"] != "High"
        and e["intent"] != "Low-Quality"
        and e["confidenceScore"] >= HIGH_PRIORITY_CONFIDENCE_FLOOR
    )
    content_gaps = sum(1 for e in entries if e["contentGapCandidate"])
    compliance_flagged = sum(1 for e in entries if e["complianceRisk"] == "High")
    avg_confidence = round(sum(e["confidenceScore"] for e in entries) / total, 1) if total else 0.0
    return {
        "totalKeywords": total,
        "highPriorityKeywords": high_priority,
        "contentGapsIdentified": content_gaps,
        "complianceRiskFlagged": compliance_flagged,
        "avgConfidenceScore": avg_confidence,
    }


def kpi_deltas(current, previous):
    if not previous:
        return {k: None for k in current}
    return {k: round(current[k] - previous.get(k, 0), 1) for k in current}


def top_content_gap_opportunities(entries, limit=5):
    candidates = [e for e in entries if e["contentGapCandidate"]]
    candidates.sort(key=lambda e: sum(e["coreSearchMetrics"]["volumeByCountry"].values()), reverse=True)
    return [
        {
            "keyword": e["keyword"],
            "totalVolume": sum(e["coreSearchMetrics"]["volumeByCountry"].values()),
            "parentTopic": e["parentTopic"],
        }
        for e in candidates[:limit]
    ]


def build_avoid_list(entries):
    avoid = []
    for e in entries:
        reasons = []
        if e["spamRisk"] == "Flagged":
            reasons.append("Spam/low-quality-intent vocabulary")
        if e["intent"] == "Low-Quality" and e["spamRisk"] == "None":
            reasons.append("DIY/home-remedy or job-seeker intent")
        if reasons:
            avoid.append({"keyword": e["keyword"], "reasons": reasons, "intent": e["intent"]})
    return avoid


def build_competitor_gap_list(entries):
    return [
        {
            "keyword": e["keyword"],
            "competitor": e["competitorGap"]["competitor"],
            "competitorPosition": e["competitorGap"]["competitorPosition"],
            "ourPosition": e["competitorGap"]["ourPosition"],
        }
        for e in entries if e["competitorGap"]
    ]


def build_underperforming_list(entries, page_titles):
    return [
        {
            "keyword": e["keyword"],
            "mappedPage": page_titles.get(e["mappedPageId"], e["mappedPage"]),
            "position": e["coreSearchMetrics"]["currentRankingPosition"],
            "confidenceScore": e["confidenceScore"],
        }
        for e in entries if e["underperformanceFlag"]
    ]


def js_const(name, obj):
    dumped = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    dumped = dumped.replace("</script>", "<\\/script>")
    return f"const {name} = {dumped};"


def build(phase):
    semrush = fetch_semrush.fetch(phase)
    gsc = fetch_gsc.fetch(phase)
    ga4 = fetch_ga4.fetch(phase)
    ads = fetch_google_ads_search_terms.fetch(phase)
    suggest_proxy = fetch_google_suggest_proxy.fetch(phase)
    competitor_keywords = fetch_competitor_keywords.fetch(phase)

    trending_phrases = collect_trending_phrases(suggest_proxy)
    page_titles = page_title_by_id()

    entries = [
        build_entry(keyword, semrush_data, gsc, ga4, ads, competitor_keywords, trending_phrases, page_titles)
        for keyword, semrush_data in semrush.items()
    ]

    cannibalized = competitor_and_gap.detect_cannibalization(entries)
    for e in entries:
        if e["keyword"] in cannibalized:
            e["competitorContentGap"]["cannibalizationRisk"] = True

    history = load_history()
    position_history = history.get("positionHistory", {})
    needs_attention = rules.generate_needs_attention(entries, position_history)

    kpis = compute_kpis(entries)
    previous_kpis = history.get("kpiHistory", [])[-1] if history.get("kpiHistory") else None
    deltas = kpi_deltas(kpis, previous_kpis)

    today = date.today().isoformat()
    new_kpi_history = (history.get("kpiHistory") or []) + [dict(kpis, date=today)]
    new_position_history = dict(position_history)
    for e in entries:
        pos = e["coreSearchMetrics"]["currentRankingPosition"]
        if pos is None:
            continue
        points = new_position_history.get(e["keyword"], [])
        points = points + [{"date": today, "position": pos}]
        new_position_history[e["keyword"]] = points[-MAX_POSITION_HISTORY_POINTS:]

    output_data = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "phase": phase,
        "kpis": kpis,
        "kpiDeltas": deltas,
        "entries": entries,
        "needsAttention": needs_attention,
        "topContentGapOpportunities": top_content_gap_opportunities(entries),
        "avoidList": build_avoid_list(entries),
        "competitorGapList": build_competitor_gap_list(entries),
        "underperformingPages": build_underperforming_list(entries, page_titles),
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    new_history = {"kpiHistory": new_kpi_history[-12:], "positionHistory": new_position_history}
    with open(HISTORY_JSON, "w", encoding="utf-8") as f:
        json.dump(new_history, f, ensure_ascii=False, indent=2)

    html = render_html(output_data, js_const)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Built {OUTPUT_HTML} ({len(entries)} keywords, phase={phase})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["sample", "live"], default="sample")
    args = parser.parse_args()
    build(args.phase)
