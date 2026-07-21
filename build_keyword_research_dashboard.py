"""
Orchestrator: load fetcher output (sample or live) -> merge into one entry
per keyword -> run every analysis module -> compute KPIs + Needs Attention
alerts + history deltas -> write data/keyword_research_data.json +
data/keyword_history.json -> emit the self-contained static index.html
(named index.html, not keyword-research-dashboard.html, so Vercel serves it
at the domain root with zero output-directory/rewrite configuration).

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
from analysis import competitor_and_gap, rules
from analysis.entry_builder import build_entry, resolve_ga4_entry
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
OUTPUT_HTML = os.path.join(ROOT, "index.html")

MAX_POSITION_HISTORY_POINTS = 8


def load_history():
    if os.path.exists(HISTORY_JSON):
        with open(HISTORY_JSON, encoding="utf-8") as f:
            return json.load(f)
    with open(os.path.join(SAMPLE_DIR, "keyword_history_sample.json"), encoding="utf-8") as f:
        return json.load(f)


def page_title_by_id():
    return {p["id"]: p["title"] for p in config.PAGES}


def collect_trending_phrases(suggest_proxy_data):
    trending = set()
    for seed_data in suggest_proxy_data.values():
        trending.update(seed_data.get("trending", []))
    return trending


def compute_kpis(entries):
    total = len(entries)
    high_priority = sum(1 for e in entries if e["priority"] == "High")
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
        build_entry(
            keyword, semrush_data, gsc.get(keyword),
            resolve_ga4_entry(phase, keyword, gsc.get(keyword), ga4), ads.get(keyword),
            competitor_and_gap.competitor_overlap(keyword, competitor_keywords),
            trending_phrases, page_titles,
        )
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
