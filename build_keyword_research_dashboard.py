"""
Orchestrator: for every registered brand (config.BRANDS) -- load fetcher
output (sample or live) -> merge into one entry per keyword -> run every
analysis module with that brand's business context -> compute KPIs +
Needs Attention alerts + history deltas -> write
data/keyword_research_data_<brand>.json + data/keyword_history_<brand>.json
-- then emit ONE self-contained static index.html with every brand's data
baked in (named index.html, not keyword-research-dashboard.html, so
Vercel serves it at the domain root with zero output-directory/rewrite
configuration).

Usage:
    python build_keyword_research_dashboard.py                    # all brands, --phase sample (default)
    python build_keyword_research_dashboard.py --phase live       # all brands, live (weekly GitHub Actions run)
    python build_keyword_research_dashboard.py --phase live --brand villaraag   # one brand only (local testing) --
        writes just that brand's data file, then re-renders index.html using
        whichever brands already have a data file on disk (doesn't require
        or touch brands you haven't built locally).

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
OUTPUT_HTML = os.path.join(ROOT, "index.html")

MAX_POSITION_HISTORY_POINTS = 8


def _output_json_path(brand_key):
    return os.path.join(DATA_DIR, f"keyword_research_data_{brand_key}.json")


def _history_json_path(brand_key):
    return os.path.join(DATA_DIR, f"keyword_history_{brand_key}.json")


def load_history(brand_key):
    path = _history_json_path(brand_key)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    if brand_key == "healing_village":
        with open(os.path.join(SAMPLE_DIR, "keyword_history_sample.json"), encoding="utf-8") as f:
            return json.load(f)
    return {"kpiHistory": [], "positionHistory": {}}


def page_title_by_id(brand):
    return {p["id"]: p["title"] for p in brand.pages}


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


def build_brand_data(phase, brand):
    """Returns one brand's full output_data dict (same shape the dashboard
    HTML/JS expects) and writes it to disk -- or returns None and writes
    nothing if the fetch produced zero entries (e.g. sample phase for a
    brand with no sample fixture yet, like Villaraag today), so a no-data
    run never clobbers a previously-good data file with an empty one."""
    semrush = fetch_semrush.fetch(phase, brand)
    gsc = fetch_gsc.fetch(phase, brand)
    ga4 = fetch_ga4.fetch(phase, brand)
    ads = fetch_google_ads_search_terms.fetch(phase, brand)
    suggest_proxy = fetch_google_suggest_proxy.fetch(phase, brand)
    competitor_keywords = fetch_competitor_keywords.fetch(phase, brand)

    trending_phrases = collect_trending_phrases(suggest_proxy)
    page_titles = page_title_by_id(brand)

    entries = [
        build_entry(
            keyword, semrush_data, gsc.get(keyword),
            resolve_ga4_entry(phase, keyword, gsc.get(keyword), ga4), ads.get(keyword),
            competitor_and_gap.competitor_overlap(keyword, competitor_keywords),
            trending_phrases, page_titles, brand,
        )
        for keyword, semrush_data in semrush.items()
    ]

    if not entries:
        print(f"Skipping {brand.key}: no keyword data for phase={phase} (leaving any existing data file untouched)")
        return None

    cannibalized = competitor_and_gap.detect_cannibalization(entries)
    for e in entries:
        if e["keyword"] in cannibalized:
            e["competitorContentGap"]["cannibalizationRisk"] = True

    history = load_history(brand.key)
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
    with open(_output_json_path(brand.key), "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    new_history = {"kpiHistory": new_kpi_history[-12:], "positionHistory": new_position_history}
    with open(_history_json_path(brand.key), "w", encoding="utf-8") as f:
        json.dump(new_history, f, ensure_ascii=False, indent=2)

    return output_data


def build(phase, brand_key=None):
    brand_keys = [brand_key] if brand_key else list(config.BRANDS.keys())
    built_counts = {}
    for key in brand_keys:
        brand = config.BRANDS[key]
        output_data = build_brand_data(phase, brand)
        if output_data is not None:
            built_counts[key] = len(output_data["entries"])

    # The brand SELECTOR always lists every registered brand, regardless of
    # whether a weekly data file exists yet -- the Search tool is live/on-
    # demand and doesn't need one (see api/search.py), so a brand-new
    # brand must be selectable there immediately. BRAND_DATA (the actual
    # Weekly Report payload) only includes brands that currently have a
    # data file on disk; dashboard_html.py's renderAll() shows a clear
    # "no report yet" state for any brand missing from it instead of
    # crashing or silently showing another brand's data.
    brand_list = [{"key": key, "label": brand.label} for key, brand in config.BRANDS.items()]
    brand_data = {}
    for key in config.BRANDS:
        path = _output_json_path(key)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            brand_data[key] = json.load(f)

    html = render_html(brand_data, brand_list, js_const)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    summary = ", ".join(f"{k}={v}" for k, v in built_counts.items())
    print(f"Built {OUTPUT_HTML} ({summary} keywords, phase={phase}, brands in HTML: {list(brand_data.keys())})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["sample", "live"], default="sample")
    parser.add_argument("--brand", choices=list(config.BRANDS.keys()), default=None)
    args = parser.parse_args()
    build(args.phase, args.brand)
