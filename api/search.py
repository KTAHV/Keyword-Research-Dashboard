"""
Vercel Python serverless function: POST /api/search
Body: {"seedKeyword": str, "url": str, "content": str} -- any subset filled.

Runs live/on-demand (unlike the weekly batch): expands whichever input the
user filled in into candidate keyword phrases -- via Claude (real semantic
understanding of the topic, see analysis/ai_keyword_ideation.py) if
ANTHROPIC_API_KEY is set, else a regex-based fallback -- looks them up in
Semrush (live if SEMRUSH_API_KEY is set, otherwise a labelled "demo" match
against the local sample keyword universe), cross-references any hits
against the last weekly-committed data/keyword_research_data.json for
GSC/GA4/Ads signal, scores everything through the same analysis/ pipeline
the batch build uses (via analysis/entry_builder.py so the two paths can't
drift apart), and returns a priority-sorted list. The `ideation` field on
the response ("ai" | "basic") and `mode` field ("live" | "demo") are
independent -- Claude and Semrush are separate credentials, either can be
present without the other.

Static HTML can't call Semrush/GSC/GA4/Ads directly -- the API keys and
OAuth secrets can't safely live in browser JS, and most of these APIs block
direct browser calls anyway (CORS). This function is the server-side half
that makes the Search tool in dashboard_html.py's #viewSearch actually work.
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import config  # noqa: E402
from analysis import ai_keyword_ideation  # noqa: E402
from analysis.entry_builder import build_entry, enrich_with_cached_signal  # noqa: E402
from analysis.phrase_extraction import content_words, extract_page_text, extract_seed_phrases  # noqa: E402
from fetchers import semrush_client  # noqa: E402

MAX_SEED_PHRASES = 6  # cap for the regex-fallback path (each seed expands via Semrush related-terms)
MAX_AI_KEYWORDS = 20  # cap for the AI-ideation path (each is looked up directly, no expansion needed)
DEMO_SEMRUSH_PATH = os.path.join(ROOT, "data", "sample", "semrush_keywords_sample.json")
CACHED_DATA_PATH = os.path.join(ROOT, "data", "keyword_research_data.json")


def _load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _page_titles():
    return {p["id"]: p["title"] for p in config.PAGES}


def _fetch_url_text(url):
    import requests
    from bs4 import BeautifulSoup

    resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0 (KeywordResearchBot)"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    return extract_page_text(soup)


def _demo_semrush_lookup(seed_phrases):
    """Word-overlap matching (not strict substring) against the local sample
    keyword universe -- a seed like "kairali ayurvedic" now matches sample
    keywords sharing any significant word ("ayurvedic", "kairali", ...)
    instead of requiring one string to literally contain the other. Demo
    mode exists to show the tool's shape without a Semrush key; returning
    zero results whenever the seed isn't an exact substring defeated that
    purpose."""
    universe = _load_json(DEMO_SEMRUSH_PATH) or {}
    seed_word_sets = [set(content_words(p)) for p in seed_phrases]
    seed_word_sets = [s for s in seed_word_sets if s]
    matched = {}
    for kw, data in universe.items():
        if kw == "_note":
            continue
        candidate_words = set(content_words(kw))
        if any(words & candidate_words for words in seed_word_sets):
            matched[kw] = data
    return matched


def _live_semrush_related_lookup(seed_phrases, api_key):
    """Fallback path (no AI ideation available): expand each regex-derived
    seed phrase via Semrush's own related-keywords endpoint."""
    matched = {}
    warnings = []
    for phrase in seed_phrases:
        try:
            overview = semrush_client.fetch_phrase_overview(phrase, api_key, database="in")
            if overview:
                matched[overview["keyword"]] = {
                    "volumeByCountry": {"in": overview["volume"]},
                    "cpc": overview["cpc"],
                    "difficulty": overview["difficulty"],
                    "parentTopic": phrase,
                }
            related = semrush_client.fetch_related_keywords(phrase, api_key, database="in", limit=10)
            for r in related:
                matched.setdefault(r["keyword"], {
                    "volumeByCountry": {"in": r["volume"]},
                    "cpc": r["cpc"],
                    "difficulty": r["difficulty"],
                    "parentTopic": phrase,
                })
        except Exception as exc:
            warnings.append(f"Semrush lookup failed for '{phrase}': {exc}")
    return matched, warnings


def _live_semrush_overview_lookup(keywords, api_key):
    """AI-ideation path: Claude already did the semantic expansion, so each
    candidate just needs its own Semrush overview (volume/CPC/difficulty) --
    no further related-keyword expansion, which keeps Semrush API-unit cost
    proportional to the AI's candidate count instead of multiplying it."""
    matched = {}
    warnings = []
    for keyword in keywords:
        try:
            overview = semrush_client.fetch_phrase_overview(keyword, api_key, database="in")
            if overview and overview["volume"] > 0:
                matched[overview["keyword"]] = {
                    "volumeByCountry": {"in": overview["volume"]},
                    "cpc": overview["cpc"],
                    "difficulty": overview["difficulty"],
                    "parentTopic": keyword,
                }
        except Exception as exc:
            warnings.append(f"Semrush lookup failed for '{keyword}': {exc}")
    return matched, warnings


def _dedupe_phrases(phrases):
    seen = set()
    deduped = []
    for p in phrases:
        key = p.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(p)
    return deduped


def run_search(body):
    seed_keyword = (body.get("seedKeyword") or "").strip()
    url = (body.get("url") or "").strip()
    content = (body.get("content") or "").strip()

    warnings = []
    resolved_text = ""

    if content:
        resolved_text = content
    elif url:
        try:
            resolved_text = _fetch_url_text(url)
        except Exception as exc:
            return {"error": f"Could not fetch that URL: {exc}"}

    if not seed_keyword and not resolved_text:
        return {"error": "Type a seed keyword, paste a URL, or paste some content first."}

    # Ideation: prefer Claude's semantic expansion (real understanding of the
    # topic) over the regex-based n-gram fallback. Falls back silently to the
    # simpler path if ANTHROPIC_API_KEY is unset or the call fails, so the
    # tool still works either way.
    ideation = "basic"
    ai_input = ai_keyword_ideation.build_input_text(seed_keyword, resolved_text)
    try:
        ai_keywords = ai_keyword_ideation.suggest_keywords(ai_input)
        seed_phrases = _dedupe_phrases(([seed_keyword] if seed_keyword else []) + ai_keywords)
        seed_phrases = seed_phrases[:MAX_AI_KEYWORDS]
        ideation = "ai"
    except Exception as exc:
        warnings.append(f"AI keyword ideation unavailable ({exc}) -- using basic phrase extraction instead.")
        seed_phrases = []
        if seed_keyword:
            seed_phrases.append(seed_keyword)
        if resolved_text:
            seed_phrases.extend(extract_seed_phrases(resolved_text, limit=5))
        seed_phrases = _dedupe_phrases(seed_phrases)[:MAX_SEED_PHRASES]

    if not seed_phrases:
        return {"error": "Type a seed keyword, paste a URL, or paste some content first."}

    api_key = os.environ.get("SEMRUSH_API_KEY")
    mode = "live" if api_key else "demo"

    if mode == "live":
        if ideation == "ai":
            semrush_matches, semrush_warnings = _live_semrush_overview_lookup(seed_phrases, api_key)
        else:
            semrush_matches, semrush_warnings = _live_semrush_related_lookup(seed_phrases, api_key)
        warnings.extend(semrush_warnings)
        warnings.append(
            "Live mode prices India (in) search volume only, to bound Semrush API-unit cost per search."
        )
    else:
        semrush_matches = _demo_semrush_lookup(seed_phrases)
        warnings.append(
            "Demo data -- SEMRUSH_API_KEY isn't set in Vercel yet, so these are sample keywords, "
            "not a live Semrush lookup."
        )

    if not semrush_matches:
        return {
            "mode": mode,
            "ideation": ideation,
            "resolvedSeeds": seed_phrases,
            "warnings": warnings + ["No matching keywords found for these seeds."],
            "entries": [],
        }

    cached_data = _load_json(CACHED_DATA_PATH)
    cached_by_keyword = {e["keyword"]: e for e in (cached_data or {}).get("entries", [])}
    page_titles = _page_titles()

    if not cached_data:
        warnings.append(
            "No weekly-refresh dataset found yet -- GSC/GA4/Ads cross-reference is unavailable "
            "until the first weekly build runs."
        )

    entries = []
    for keyword, semrush_data in semrush_matches.items():
        entry = build_entry(keyword, semrush_data, None, None, None, None, set(), page_titles)
        entry = enrich_with_cached_signal(entry, cached_by_keyword.get(keyword))
        entries.append(entry)

    priority_rank = {"High": 0, "Medium": 1, "Low": 2}
    entries.sort(key=lambda e: (priority_rank.get(e["priority"], 3), -e["confidenceScore"]))

    return {
        "mode": mode,
        "ideation": ideation,
        "resolvedSeeds": seed_phrases,
        "warnings": warnings,
        "entries": entries,
    }


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            body = json.loads(raw or b"{}")
        except (ValueError, TypeError):
            self._send_json({"error": "Invalid request body."}, status=400)
            return

        try:
            result = run_search(body)
        except Exception as exc:  # last-resort guard -- the endpoint should never 500 silently
            self._send_json({"error": f"Search failed: {exc}"}, status=500)
            return

        status = 400 if "error" in result and "entries" not in result else 200
        self._send_json(result, status=status)

    def do_GET(self):
        self._send_json({"error": "Use POST with a JSON body: {seedKeyword, url, content}."}, status=405)

    def _send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
