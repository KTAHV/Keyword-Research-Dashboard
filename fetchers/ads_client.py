"""
Shared Google Ads client construction -- used by both
fetch_google_ads_search_terms.py (search_term_view GAQL) and
keyword_planner_client.py (KeywordPlanIdeaService), so the credential path
and error message are defined once.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ads_yaml_path():
    # Overridable so api/search.py (Vercel -- read-only filesystem except
    # /tmp) can point this at a request-time-materialized file instead of
    # the repo root, which GitHub Actions writes to instead.
    return os.environ.get("GOOGLE_ADS_YAML_PATH") or os.path.join(ROOT, "google-ads.yaml")


def get_client():
    from google.ads.googleads.client import GoogleAdsClient

    path = ads_yaml_path()
    if not os.path.exists(path):
        raise RuntimeError(
            f"{path} not found -- run scripts/get_ads_refresh_token.py locally "
            "and build a google-ads.yaml (see that script's module docstring), "
            "or confirm scripts/write_credentials.py ran (CI with the "
            "GOOGLE_ADS_* secrets set, or api/search.py's request-time "
            "materialization)."
        )
    return GoogleAdsClient.load_from_storage(path)
