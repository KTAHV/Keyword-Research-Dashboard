"""
Google Ads Search Terms Report: paid, human-verified queries with
impressions/clicks/cost/conversions/matchType. Presence here (regardless of
score) is strong evidence a query is a real, converting search -- and,
conversely, high spend with near-zero conversions (see
"ayurvedic massage near me" in the sample fixture) is direct evidence for why
a spam-adjacent term belongs on the Avoid List even though the paid team
already tried it.

Phase "sample": reads data/sample/google_ads_search_terms_sample.json.

Phase "live": same search_term_view GAQL query as Combined Marketing
Dashboard/Kairali Google ad/fetch_search_terms.py, against
config.ADS_CUSTOMER_ID. Credential loading is shared with
keyword_planner_client.py -- see fetchers/ads_client.py.
"""
import config
from fetchers import ads_client
from fetchers._util import load_sample

QUERY = """
    SELECT
        search_term_view.search_term,
        segments.search_term_match_type,
        metrics.cost_micros,
        metrics.clicks,
        metrics.conversions,
        metrics.impressions
    FROM search_term_view
    WHERE segments.date DURING {lookback}
"""


def _fetch_live():
    client = ads_client.get_client()
    ga_service = client.get_service("GoogleAdsService")
    query = QUERY.format(lookback=config.ADS_LOOKBACK)

    result = {}
    for row in ga_service.search(customer_id=config.ADS_CUSTOMER_ID, query=query):
        term = row.search_term_view.search_term.strip().lower()
        result[term] = {
            "impressions": row.metrics.impressions,
            "clicks": row.metrics.clicks,
            "cost": round(row.metrics.cost_micros / 1_000_000, 2),
            "conversions": round(row.metrics.conversions),
            "matchType": row.segments.search_term_match_type.name,
        }
    return result


def fetch(phase="sample"):
    if phase == "live":
        return _fetch_live()
    return load_sample("google_ads_search_terms_sample.json")
