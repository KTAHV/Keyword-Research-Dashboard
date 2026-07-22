"""
Google Search Console: per-query impressions/clicks/ctr/position, plus which
mapped page (if any) currently ranks for that query.

Phase "sample": reads data/sample/gsc_queries_sample.json.

Phase "live": raw REST `searchAnalytics.query` via AuthorizedSession -- same
pattern as Combined Marketing Dashboard/GSC Dashboard/fetch_gsc_data.py and
fetch_url_health_cwv.py (not google-api-python-client's build()). Queried
for every brand.gsc_site_urls property and merged into one dict keyed by
the exact query string. The returned page URL is matched back to a
brand.pages entry (or None if it doesn't match any tracked page -- that's
a Content Gap candidate). Same shared OAuth client/refresh token for every
brand (see scripts/authenticate_all.py) -- only the target site URLs differ.

Needs token_gsc.json in the repo root (see scripts/authenticate_gsc.py for
the one-time OAuth setup, or scripts/write_credentials.py for how CI
materializes it from the GSC_REFRESH_TOKEN GitHub Actions secret).
"""
import json
import os
import time
from datetime import date, timedelta
from urllib.parse import quote, urlparse

import config
from fetchers._util import load_sample

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _token_path():
    # Overridable so api/search.py (Vercel -- read-only filesystem except
    # /tmp) can point this at a request-time-materialized token file
    # instead of the repo root, which GitHub Actions writes to instead.
    return os.environ.get("TOKEN_GSC_PATH") or os.path.join(ROOT, "token_gsc.json")


def load_credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    token_path = _token_path()
    if not os.path.exists(token_path):
        raise RuntimeError(
            f"{token_path} not found -- run scripts/authenticate_gsc.py locally, "
            "or confirm scripts/write_credentials.py ran (CI with GSC_REFRESH_TOKEN "
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


def _query_site(session, site, start, end, row_limit=25000, retries=4):
    url = f"https://www.googleapis.com/webmasters/v3/sites/{quote(site, safe='')}/searchAnalytics/query"
    body = {
        "startDate": start, "endDate": end, "dimensions": ["query", "page"],
        "rowLimit": row_limit, "dataState": "all",
    }
    for attempt in range(retries):
        resp = session.post(url, json=body, timeout=30)
        if resp.ok:
            return resp.json().get("rows", [])
        if resp.status_code in (429, 500, 503) and attempt < retries - 1:
            time.sleep(1.5 * (attempt + 1))
            continue
        raise RuntimeError(f"GSC query failed for {site}: {resp.status_code} {resp.text[:200]}")
    return []


def _normalize_url(url):
    parsed = urlparse(url if "//" in url else f"//{url}")
    host = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path.rstrip("/")
    return f"{host}{path}"


def _match_page_id(page_url, brand):
    normalized = _normalize_url(page_url)
    for page in brand.pages:
        if _normalize_url(page["url"]) == normalized:
            return page["id"]
    return None


def _fetch_live(brand):
    from google.auth.transport.requests import AuthorizedSession

    creds = load_credentials()
    session = AuthorizedSession(creds)

    end_date = date.today() - timedelta(days=config.GSC_DATA_LAG_DAYS)
    start_date = end_date - timedelta(days=config.GSC_LOOKBACK_DAYS)

    merged = {}
    for site in brand.gsc_site_urls:
        rows = _query_site(session, site, start_date.isoformat(), end_date.isoformat())
        for row in rows:
            query, page_url = row["keys"]
            impressions = row.get("impressions", 0)
            clicks = row.get("clicks", 0)
            position = row.get("position", 0)

            entry = merged.setdefault(query, {
                "impressions": 0, "clicks": 0, "_position_weighted_sum": 0.0, "page": None,
            })
            entry["impressions"] += impressions
            entry["clicks"] += clicks
            entry["_position_weighted_sum"] += position * max(impressions, 1)
            if entry["page"] is None:
                entry["page"] = _match_page_id(page_url, brand)

    result = {}
    for query, entry in merged.items():
        impressions = entry["impressions"]
        result[query] = {
            "impressions": impressions,
            "clicks": entry["clicks"],
            "ctr": round((entry["clicks"] / impressions) * 100, 2) if impressions else 0.0,
            "position": round(entry["_position_weighted_sum"] / max(impressions, 1), 1),
            "page": entry["page"],
        }
    return result


def fetch(phase, brand):
    if phase == "live":
        return _fetch_live(brand)
    if brand.key == "healing_village":
        return load_sample("gsc_queries_sample.json")
    return {}
