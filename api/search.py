"""
Vercel Python serverless function: POST /api/search
Body: {"brand": str, "seedKeyword": str, "url": str, "content": str} --
`brand` is one of config.BRANDS's keys (defaults to config.DEFAULT_BRAND
if omitted, for backward compatibility with any cached client). Any
subset of seedKeyword/url/content may be filled.

Runs live/on-demand (unlike the weekly batch):

1. Ideation -- Claude proposes candidate keyword phrases using the
   selected brand's persona (analysis/ai_keyword_ideation.py,
   brand.ai_system_prompt) if ANTHROPIC_API_KEY is set, else a regex-based
   fallback (analysis/phrase_extraction.py).
2. Compliance filter -- candidates matching "patient(s)" + a specific
   nationality/country name are dropped entirely before scoring (see
   analysis/compliance.py::is_patient_nationality_pattern; empty for
   brands with no nationality_country_terms, e.g. Villaraag). Separately,
   a *typed seed keyword* matching brand.restricted_seed_terms (each
   brand's own sourced policy list) is never searched at all -- the
   request returns a "policyNotice" and swaps in a brand-appropriate
   fallback seed so the user still gets a full table of compliant
   suggestions instead of the blocked term.
3. Semrush discovery -- `phrase_related` (real, volume-backed discovery,
   not exact-match) on the shortest/primary seed, across every database in
   config.SEMRUSH_SEARCH_DATABASES, PLUS a best-effort `phrase_this` exact
   lookup per AI-suggested candidate (a miss is expected and ignored, not
   an error -- see fetchers/semrush_client.py's module docstring for why
   the earlier exact-match-only design returned almost nothing).
4. Google Keyword Planner fallback -- for any AI-suggested candidate still
   missing volume after step 3, if Google Ads credentials are available
   (fetchers/keyword_planner_client.py), targeting brand.ads_customer_id.
5. Live GSC + Ads cross-reference -- if Google credentials are available,
   queries them live (not just the cached weekly snapshot) for
   position/mapped-page/paid-verification signal, targeting the selected
   brand's GSC site URLs / Ads customer ID. GA4 is deliberately excluded
   from this live path: GA4 has no native search-query dimension (only
   GSC does), so a per-search GA4 lookup here would be page-level-only
   and couldn't actually be attributed to the searched keyword the way
   GSC and Ads can. GA4 signal only ever reaches an entry via the cached
   weekly snapshot (enrich_with_cached_signal, when the keyword already
   exists in that brand's last week's build) -- never a live call from
   this endpoint.
6. Scores everything through the same analysis/ pipeline the batch build
   uses (analysis/entry_builder.py, so the two paths can't drift apart),
   passing the selected brand through so compliance/spam/audience-fit
   logic matches that brand's business context, attaches a Search-Volume +
   source label per entry, and returns a priority-sorted list.

Static HTML can't call Semrush/Claude/GSC/GA4/Ads directly -- the API keys
and OAuth secrets can't safely live in browser JS, and most of these APIs
block direct browser calls anyway (CORS). This function is the server-side
half that makes the Search tool in dashboard_html.py's #viewSearch work.

Vercel's filesystem is read-only except /tmp -- live Google credentials
(if configured) are materialized there at request time via
scripts/write_credentials.py, then the existing fetchers (fetch_gsc.py,
fetch_ga4.py, fetch_google_ads_search_terms.py -- the same ones used by
the weekly batch) are pointed at /tmp via their env-var path overrides.
Nothing here is ever committed. Every brand shares the same OAuth client/
refresh tokens (confirmed this session against the sibling Combined
Marketing Dashboard repo's per-brand credential files) -- only the
target GSC site/GA4 property/Ads customer ID differs per brand, which is
config, not credentials.
"""
import json
import os
import sys
import tempfile
from http.server import BaseHTTPRequestHandler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import config  # noqa: E402
from analysis import ai_keyword_ideation, compliance  # noqa: E402
from analysis.entry_builder import build_entry, enrich_with_cached_signal  # noqa: E402
from analysis.phrase_extraction import extract_page_text, extract_seed_phrases  # noqa: E402
from fetchers import fetch_google_ads_search_terms, fetch_gsc, keyword_planner_client, semrush_client  # noqa: E402
from scripts import write_credentials  # noqa: E402

MAX_SEED_PHRASES = 6  # cap for the regex-fallback path (no AI available)
MAX_AI_KEYWORDS = 25  # cap for AI-ideation candidates; kept above the ~20-in-table target
# since compliance exclusions and dedup can trim the list before it reaches the table.
# keyword_planner_client.py slices its own MAX_KEYWORDS_PER_CALL internally, so this
# doesn't overrun that API's per-call limit.

# Used in place of a seed that matches brand.restricted_seed_terms, so a
# blocked search still produces a full table of compliant suggestions for
# that brand specifically (not a generic/wrong-brand fallback).
_FALLBACK_SAFE_SEEDS = {
    "healing_village": "ayurvedic healing village treatments and wellness programs",
    "villaraag": "villaraag luxury villa resort yoga and wellness retreat goa",
}


def _fallback_safe_seed(brand):
    return _FALLBACK_SAFE_SEEDS.get(brand.key, f"{brand.label} services")


def _demo_semrush_path(brand):
    return os.path.join(ROOT, "data", "sample", "semrush_keywords_sample.json") if brand.key == "healing_village" else None


def _cached_data_path(brand):
    return os.path.join(ROOT, "data", f"keyword_research_data_{brand.key}.json")


def _load_json(path):
    if not path or not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _page_titles(brand):
    return {p["id"]: p["title"] for p in brand.pages}


def _fetch_url_text(url):
    import requests
    from bs4 import BeautifulSoup

    resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0 (KeywordResearchBot)"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    return extract_page_text(soup)


def _demo_semrush_lookup(seed_phrases, brand):
    """Word-overlap matching (not strict substring) against the local
    sample keyword universe -- demo mode exists to show the tool's shape
    without a Semrush key. Only Healing Village has a sample fixture
    today; other brands get {} in demo mode (real live mode doesn't need
    one -- see fetch_semrush.py)."""
    from analysis.phrase_extraction import content_words

    path = _demo_semrush_path(brand)
    if not path:
        return {}
    universe = _load_json(path) or {}
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


def _dedupe_phrases(phrases):
    seen = set()
    deduped = []
    for p in phrases:
        key = p.lower().strip()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(p)
    return deduped


def _resolve_candidates(seed_keyword, resolved_text, brand):
    """Returns (candidates, ideation, primary_seed). `candidates` includes
    the seed keyword itself plus every ideation-sourced phrase."""
    ai_input = ai_keyword_ideation.build_input_text(seed_keyword, resolved_text)
    try:
        ai_keywords = ai_keyword_ideation.suggest_keywords(ai_input, brand)
        candidates = _dedupe_phrases(([seed_keyword] if seed_keyword else []) + ai_keywords)[:MAX_AI_KEYWORDS]
        ideation = "ai"
    except Exception:
        candidates = []
        if seed_keyword:
            candidates.append(seed_keyword)
        if resolved_text:
            candidates.extend(extract_seed_phrases(resolved_text, limit=5))
        candidates = _dedupe_phrases(candidates)[:MAX_SEED_PHRASES]
        ideation = "basic"

    if seed_keyword:
        primary_seed = seed_keyword
    elif candidates:
        primary_seed = min(candidates, key=lambda k: len(k.split()))
    else:
        primary_seed = (resolved_text or "")[:60]

    return candidates, ideation, primary_seed


def _materialize_google_credentials():
    """Best-effort. Returns a dict of which of gsc/ads got materialized
    (empty dict if GOOGLE_ADS_CLIENT_ID/SECRET aren't set at all). GA4 is
    intentionally never materialized here -- this endpoint never makes a
    live GA4 call (see module docstring); GA4_REFRESH_TOKEN only needs to
    exist in GitHub Actions secrets for the weekly batch, not in Vercel.
    Brand-agnostic: the same shared OAuth client/refresh tokens work for
    every brand, only the fetchers' *target* IDs differ per brand."""
    tmp_dir = tempfile.gettempdir()
    written = write_credentials.materialize_all(output_dir=tmp_dir)
    written.pop("ga4", None)
    if "gsc" in written:
        os.environ["TOKEN_GSC_PATH"] = written["gsc"]
    if "ads" in written:
        os.environ["GOOGLE_ADS_YAML_PATH"] = written["ads"]
    return written


def _clean_exc_message(exc, max_len=180):
    """Every warning in the response is rendered straight into the page for
    the user to read -- library exceptions (grpc, requests, ...) are often
    multi-line, full of internal debug fields, and occasionally embed
    request internals. Collapse to one short line so the Search tool's
    banner stays readable instead of dumping a stack-trace-shaped blob."""
    text = " ".join(str(exc).split())
    if len(text) > max_len:
        text = text[:max_len].rstrip() + "..."
    return text


def _fetch_live_google_signal(available, warnings, brand):
    """Live per-search GSC + Ads, used instead of the cached weekly
    snapshot when Google credentials are configured. Each source fails
    independently -- one down doesn't block the other. No GA4 call here --
    see module docstring."""
    gsc_data, ads_data = {}, {}
    if "gsc" in available:
        try:
            gsc_data = fetch_gsc.fetch("live", brand)
        except Exception as exc:
            warnings.append(f"Live GSC lookup failed: {_clean_exc_message(exc)}")
    if "ads" in available:
        try:
            ads_data = fetch_google_ads_search_terms.fetch("live", brand)
        except Exception as exc:
            warnings.append(f"Live Google Ads lookup failed: {_clean_exc_message(exc)}")
    return gsc_data, ads_data


def _seed_variants(phrase, max_variants=4):
    """phrase_related only returns data when the seed itself is
    related-keywords-indexed in Semrush -- confirmed empirically that even
    plausible 3-word phrases like "ayurveda treatment kerala" can come back
    NOTHING FOUND in every database while a 2-word subset of the same
    phrase ("ayurveda kerala") has real data. Drop one word at a time
    (keeping the rest in order) so a broader variant gets a chance instead
    of the whole discovery step giving up on one exact phrasing."""
    words = phrase.split()
    if len(words) <= 1:
        return []
    variants = []
    for i in range(len(words)):
        variant = " ".join(words[:i] + words[i + 1:])
        if variant and variant not in variants:
            variants.append(variant)
    return variants[:max_variants]


def _is_systemic_failure(errors):
    """True when fetch_related_keywords_multi_db's every-database-failed-
    identically case fires (see its docstring) -- e.g. HTTP 403 because
    this Semrush account's plan doesn't include the Related Keywords
    report at all. Retrying different seed variants against a report the
    account can't access at all would just repeat the same failure, so
    the caller should give up on discovery entirely instead of burning
    more requests."""
    return len(errors) == 1 and "Related Keywords" in errors[0] and "isn't available" in errors[0]


def _semrush_live_lookup(primary_seed, ai_candidates, api_key, warnings):
    discovered, discover_errors = semrush_client.fetch_related_keywords_multi_db(
        primary_seed, api_key, config.SEMRUSH_SEARCH_DATABASES, limit=30
    )
    warnings.extend(discover_errors)

    if not discovered and not _is_systemic_failure(discover_errors):
        for variant in _seed_variants(primary_seed):
            discovered, variant_errors = semrush_client.fetch_related_keywords_multi_db(
                variant, api_key, config.SEMRUSH_SEARCH_DATABASES, limit=30
            )
            warnings.extend(variant_errors)
            if discovered:
                break
            if _is_systemic_failure(variant_errors):
                break

    matches = dict(discovered)
    for keyword in ai_candidates:
        if keyword in matches:
            continue  # already have real discovery data for this one
        overview = semrush_client.fetch_phrase_overview_multi_db(keyword, api_key, config.SEMRUSH_SEARCH_DATABASES)
        if overview:
            matches[keyword] = overview
            continue
        # The exact AI-suggested phrase is a miss -- try a couple of its
        # shorter word-subsets too (phrase_this is exact-match, so a long
        # AI phrase like "best ayurvedic panchakarma retreat for foreign
        # patients" can miss even when a real core phrase within it, e.g.
        # "ayurvedic panchakarma retreat", is indexed). A hit here is added
        # as its own keyword entry -- its volume belongs to the variant
        # phrase, not fabricated for the original AI phrase.
        for variant in _seed_variants(keyword, max_variants=2):
            if variant in matches:
                continue
            variant_overview = semrush_client.fetch_phrase_overview_multi_db(
                variant, api_key, config.SEMRUSH_SEARCH_DATABASES
            )
            if variant_overview:
                matches[variant] = variant_overview
    return matches


def _keyword_planner_fallback(ai_candidates, matches, google_available, warnings, brand):
    if "ads" not in google_available:
        return {}
    missing = [kw for kw in ai_candidates if kw not in matches]
    if not missing:
        return {}
    try:
        kp_data = keyword_planner_client.generate_keyword_ideas(missing, brand)
    except Exception as exc:
        if "DEVELOPER_TOKEN_NOT_APPROVED" in str(exc):
            warnings.append(
                "Google Keyword Planner needs Basic/Standard API access for this Ads account "
                "(currently Test/Explorer access) -- skipped."
            )
        else:
            warnings.append(f"Google Keyword Planner fallback failed: {_clean_exc_message(exc)}")
        return {}
    # KeywordPlanIdeaService returns one combined metric across the
    # requested geo targets, not a per-country breakdown -- "kp" is a
    # source marker, not a real Semrush country code (see
    # _volume_and_source() below, which reads this same marker).
    return {
        kw: {"volumeByCountry": {"kp": data["volume"]}, "cpc": data["cpc"], "difficulty": data["competition"]}
        for kw, data in kp_data.items() if data["volume"]
    }


def _volume_and_source(mode, semrush_data):
    vol_by_country = (semrush_data or {}).get("volumeByCountry", {})
    if not vol_by_country:
        # Distinct from "Demo data" / a real source -- this candidate
        # simply has no pricing yet (e.g. Semrush's Related Keywords
        # report unavailable and no exact-match hit either), not a
        # genuinely-zero-volume keyword.
        return 0, "No volume data"
    total = sum(vol_by_country.values())
    if mode == "demo":
        return total, "Demo data"
    if "kp" in vol_by_country:
        return total, "Google Keyword Planner"
    return total, "Semrush (" + ", ".join(sorted(k.upper() for k in vol_by_country)) + ")"


def run_search(body):
    brand_key = body.get("brand") or config.DEFAULT_BRAND
    brand = config.BRANDS.get(brand_key, config.BRANDS[config.DEFAULT_BRAND])

    seed_keyword = (body.get("seedKeyword") or "").strip()
    url = (body.get("url") or "").strip()
    content = (body.get("content") or "").strip()

    warnings = []
    policy_notice = None
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

    # Restricted-keyword policy (each brand's own sourced Google-Ads/tax/
    # medical-claims doc -- see config.BrandConfig.restricted_seed_terms).
    # A seed matching this list is never searched directly: no Semrush/
    # GSC/Ads lookup runs on it at all. Instead it's swapped for a fixed
    # brand-appropriate safe seed so the user still gets a full table of
    # compliant alternative suggestions.
    seed_policy_matches = compliance.find_restricted_seed_terms(seed_keyword, brand) if seed_keyword else []
    if seed_policy_matches:
        policy_notice = (
            f"\"{seed_keyword}\" was not searched -- it matches {brand.label}'s "
            f"restricted-keyword policy: {', '.join(seed_policy_matches)}. Showing compliant "
            f"alternative suggestions for {brand.label} instead."
        )
        seed_keyword = _fallback_safe_seed(brand)
        resolved_text = ""

    candidates, ideation, primary_seed = _resolve_candidates(seed_keyword, resolved_text, brand)
    if not candidates:
        return {"error": "Type a seed keyword, paste a URL, or paste some content first.", "policyNotice": policy_notice}

    # Compliance: drop "patient(s)" + specific-nationality/country patterns
    # (no-op for brands with no nationality_country_terms), and anything
    # matching the restricted-keyword policy above, before they're ever
    # scored or shown -- see analysis/compliance.py.
    compliant_candidates = [
        k for k in candidates
        if not compliance.is_patient_nationality_pattern(k, brand) and not compliance.find_restricted_seed_terms(k, brand)
    ]
    excluded_count = len(candidates) - len(compliant_candidates)
    if excluded_count:
        warnings.append(
            f"{excluded_count} suggested keyword(s) excluded for compliance "
            "(nationality-pairing or restricted-keyword policy)."
        )
    candidates = compliant_candidates
    if not candidates:
        return {
            "mode": "demo", "brand": brand.key, "ideation": ideation, "resolvedSeeds": candidates,
            "warnings": warnings + ["All candidate keywords were excluded by the compliance filter."],
            "entries": [], "policyNotice": policy_notice,
        }

    semrush_api_key = os.environ.get("SEMRUSH_API_KEY")
    mode = "live" if semrush_api_key else "demo"

    google_available = _materialize_google_credentials()

    if mode == "live":
        matches = _semrush_live_lookup(primary_seed, candidates, semrush_api_key, warnings)
        matches.update(_keyword_planner_fallback(candidates, matches, google_available, warnings, brand))
        warnings.append(
            f"Semrush volume from {', '.join(c.upper() for c in config.SEMRUSH_SEARCH_DATABASES)}."
        )
    else:
        matches = _demo_semrush_lookup(candidates, brand)
        warnings.append(
            "Demo data -- SEMRUSH_API_KEY isn't set in Vercel yet, so these are sample keywords, "
            "not a live Semrush lookup."
        )

    # Discovery (Semrush phrase_related, demo word-overlap) can surface
    # keywords that were never in `candidates` -- re-apply both compliance
    # filters to the actual match set, not just the seed candidates, or a
    # pattern like "... for uk patients" (or a restricted-policy term) can
    # slip back in via fuzzy match.
    newly_excluded = [
        k for k in matches
        if compliance.is_patient_nationality_pattern(k, brand) or compliance.find_restricted_seed_terms(k, brand)
    ]
    if newly_excluded:
        for k in newly_excluded:
            del matches[k]
        warnings.append(
            f"{len(newly_excluded)} discovered keyword(s) excluded for compliance "
            "(nationality-pairing or restricted-keyword policy)."
        )

    # Every compliant AI-suggested candidate gets a row even if Semrush had
    # no volume for it -- Type/Placement/Intent/Compliance/AI-Voice-Fit
    # don't depend on Semrush at all, so dropping a keyword just because
    # pricing was unavailable (common now that phrase_related is 403 for
    # this account -- see semrush_client.py) throws away real, useful
    # scoring for no reason. `matches` keys not in `candidates` (real
    # discoveries/variants) are kept too and come first, since those do
    # have real volume.
    empty_semrush = {"volumeByCountry": {}, "cpc": None, "difficulty": None}
    all_keywords = dict(matches)
    for kw in candidates:
        all_keywords.setdefault(kw, empty_semrush)

    page_titles = _page_titles(brand)
    live_google = bool(google_available) and mode == "live"

    if live_google:
        gsc_data, ads_data = _fetch_live_google_signal(google_available, warnings, brand)
    else:
        cached_data = _load_json(_cached_data_path(brand))
        cached_by_keyword = {e["keyword"]: e for e in (cached_data or {}).get("entries", [])}
        if not cached_data:
            warnings.append(
                "No weekly-refresh dataset found yet -- GSC/GA4/Ads cross-reference is unavailable "
                "until the first weekly build runs."
            )

    entries = []
    for keyword, semrush_data in all_keywords.items():
        if live_google:
            gsc_entry = gsc_data.get(keyword)
            ads_entry = ads_data.get(keyword)
            entry = build_entry(keyword, semrush_data, gsc_entry, None, ads_entry, None, set(), page_titles, brand)
        else:
            entry = build_entry(keyword, semrush_data, None, None, None, None, set(), page_titles, brand)
            entry = enrich_with_cached_signal(entry, cached_by_keyword.get(keyword))
        entry["searchVolume"], entry["volumeSource"] = _volume_and_source(mode, semrush_data)
        entries.append(entry)

    priority_rank = {"High": 0, "Medium": 1, "Low": 2}
    entries.sort(key=lambda e: (priority_rank.get(e["priority"], 3), -e["searchVolume"]))

    return {
        "mode": mode,
        "brand": brand.key,
        "ideation": ideation,
        "liveGoogleCrossReference": live_google,
        "resolvedSeeds": candidates,
        "warnings": warnings,
        "entries": entries,
        "policyNotice": policy_notice,
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
        self._send_json({"error": "Use POST with a JSON body: {brand, seedKeyword, url, content}."}, status=405)

    def _send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
