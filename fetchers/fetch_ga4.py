"""
GA4: sessions/engagement-rate/conversions/avg-engagement-time, keyed by
PAGE ID (not keyword) -- GA4 has no native "search query" dimension (only
GSC does), so live GA4 signal is attributed to a keyword only when that
keyword already has a GSC-derived mapped page (see
build_keyword_research_dashboard.py's build(), which resolves
`ga4.get(gsc_entry["page"])`). Unmapped/Content-Gap keywords get no GA4
signal, same honest-gap behavior as every other unmapped source.

Phase "sample": reads data/sample/ga4_engagement_sample.json -- NOTE this
sample fixture is keyed by keyword (a Phase-1 simplification), unlike the
live path below which is keyed by page id. build()'s merge logic branches
on phase accordingly; see that module.

Phase "live": `google.analytics.data_v1beta.BetaAnalyticsDataClient.run_report()`,
same AuthorizedSession-equivalent Credentials pattern as
Combined Marketing Dashboard/GA4 Dashboard/fetch_ga4_data.py, against
brand.ga4_property_id. Needs token_ga4.json in the repo root (see
scripts/authenticate_ga4.py for the one-time OAuth setup) -- same shared
OAuth client/refresh token for every brand, only the target property
differs.
"""
import json
import os
from datetime import date, timedelta

import config
from fetchers._util import load_sample

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _token_path():
    # Overridable -- see fetch_gsc.py's _token_path() for why.
    return os.environ.get("TOKEN_GA4_PATH") or os.path.join(ROOT, "token_ga4.json")


def load_credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    token_path = _token_path()
    if not os.path.exists(token_path):
        raise RuntimeError(
            f"{token_path} not found -- run scripts/authenticate_ga4.py locally, "
            "or confirm scripts/write_credentials.py ran (CI with GA4_REFRESH_TOKEN "
            "set, or api/search.py's request-time materialization)."
        )
    with open(token_path, encoding="utf-8") as f:
        data = json.load(f)
    creds = Credentials(
        token=data["token"], refresh_token=data["refresh_token"], token_uri=data["token_uri"],
        client_id=data["client_id"], client_secret=data["client_secret"], scopes=data["scopes"],
    )
    creds.refresh(Request())
    return creds


def _match_page_id(page_path, brand):
    for page in brand.pages:
        # page["url"] is absolute (https://domain/path.html); pagePath from
        # GA4 is relative (/path.html) -- compare on the path tail only.
        if page["url"].rstrip("/").endswith(page_path.rstrip("/")) and page_path not in ("", "/"):
            return page["id"]
    return None


def _fetch_live(brand):
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, RunReportRequest

    creds = load_credentials()
    client = BetaAnalyticsDataClient(credentials=creds)

    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=config.GSC_LOOKBACK_DAYS)

    request = RunReportRequest(
        property=f"properties/{brand.ga4_property_id}",
        date_ranges=[DateRange(start_date=start_date.isoformat(), end_date=end_date.isoformat())],
        dimensions=[Dimension(name="pagePath")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="engagementRate"),
            Metric(name="conversions"),
            Metric(name="userEngagementDuration"),
        ],
        limit=100000,
    )
    response = client.run_report(request)

    result = {}
    for row in response.rows:
        page_path = row.dimension_values[0].value
        page_id = _match_page_id(page_path, brand)
        if page_id is None:
            continue
        sessions = float(row.metric_values[0].value or 0)
        engagement_rate = float(row.metric_values[1].value or 0) * 100
        conversions = float(row.metric_values[2].value or 0)
        engagement_duration = float(row.metric_values[3].value or 0)
        result[page_id] = {
            "sessions": round(sessions),
            "engagementRate": round(engagement_rate, 1),
            "conversions": round(conversions),
            "avgEngagementTimeSec": round(engagement_duration / sessions, 1) if sessions else 0.0,
        }
    return result


def fetch(phase, brand):
    if phase == "live":
        return _fetch_live(brand)
    if brand.key == "healing_village":
        return load_sample("ga4_engagement_sample.json")
    return {}
