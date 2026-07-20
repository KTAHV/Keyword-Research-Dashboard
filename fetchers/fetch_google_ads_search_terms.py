"""
Google Ads Search Terms Report: paid, human-verified queries with
impressions/clicks/cost/conversions/matchType. Presence here (regardless of
score) is strong evidence a query is a real, converting search -- and,
conversely, high spend with near-zero conversions (see
"ayurvedic massage near me" in the sample fixture) is direct evidence for why
a spam-adjacent term belongs on the Avoid List even though the paid team
already tried it.

Phase "sample": reads data/sample/google_ads_search_terms_sample.json.

Phase "live" (future): reuse Combined Marketing Dashboard/Kairali Google
ad/fetch_landing_pages.py's search-terms query verbatim, filtered to this
account. Needs GOOGLE_ADS_DEVELOPER_TOKEN/CLIENT_ID/CLIENT_SECRET/
REFRESH_TOKEN/LOGIN_CUSTOMER_ID.
"""
from fetchers._util import load_sample


def fetch(phase="sample"):
    if phase == "live":
        raise NotImplementedError(
            "Live Google Ads search-terms report fetch needs Ads credentials "
            "(see module docstring) -- not wired up yet."
        )
    return load_sample("google_ads_search_terms_sample.json")
