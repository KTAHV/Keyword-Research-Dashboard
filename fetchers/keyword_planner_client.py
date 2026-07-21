"""
Google Keyword Planner (KeywordPlanIdeaService.GenerateKeywordIdeas) -- used
only as a fallback for the live Search tool's AI-suggested keywords that
Semrush has no volume for (see api/search.py). This is the same API behind
Google Ads' "Discover new keywords" UI.

Every field/type referenced here was verified against the installed
google-ads==31.1.0 package (API v24, the client library's default) in this
session: `client.get_type("KeywordSeed")` takes `.keywords` (max 20 per
call), `client.get_type("GenerateKeywordIdeasRequest")` takes
`.customer_id`/`.keyword_seed`/`.geo_target_constants`, and each response
row carries `.text` and `.keyword_idea_metrics`
(avg_monthly_searches/competition_index/average_cpc_micros).

Geo targeting uses config.KEYWORD_PLANNER_GEO_TARGETS -- standard, stable
IDs I could not verify against a live account in this environment (no
credentials here). If the API rejects them, retries once without geo
targeting rather than failing the whole search.
"""
import config
from fetchers import ads_client

MAX_KEYWORDS_PER_CALL = 20  # Google Ads API limit for KeywordSeed.keywords


def _run(keywords, client, use_geo_targeting):
    idea_service = client.get_service("KeywordPlanIdeaService")

    keyword_seed = client.get_type("KeywordSeed")
    keyword_seed.keywords.extend(keywords)

    request = client.get_type("GenerateKeywordIdeasRequest")
    request.customer_id = config.ADS_CUSTOMER_ID
    request.keyword_seed = keyword_seed
    request.include_adult_keywords = False
    if use_geo_targeting:
        request.geo_target_constants.extend(config.KEYWORD_PLANNER_GEO_TARGETS)

    return idea_service.generate_keyword_ideas(request=request)


def generate_keyword_ideas(keywords):
    """keywords: list of strings (only the first MAX_KEYWORDS_PER_CALL are
    used -- caller should already have narrowed to "still missing volume"
    candidates). Returns a dict keyed by lowercased keyword text ->
    {volume, competition (0-100 index or None), cpc (cents or None)}."""
    if not keywords:
        return {}

    client = ads_client.get_client()
    keywords = keywords[:MAX_KEYWORDS_PER_CALL]

    try:
        response = _run(keywords, client, use_geo_targeting=True)
    except Exception:
        response = _run(keywords, client, use_geo_targeting=False)

    result = {}
    for row in response:
        text = (row.text or "").strip().lower()
        if not text:
            continue
        metrics = row.keyword_idea_metrics
        avg_cpc_dollars = metrics.average_cpc_micros / 1_000_000 if metrics.average_cpc_micros else None
        result[text] = {
            "volume": metrics.avg_monthly_searches or 0,
            "competition": metrics.competition_index if metrics.competition_index is not None else None,
            "cpc": round(avg_cpc_dollars * 100) if avg_cpc_dollars else None,
        }
    return result
