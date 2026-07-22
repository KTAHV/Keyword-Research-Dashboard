"""
Semrush: the broad keyword universe -- volume by country, CPC, difficulty
-- for each brand's fixed known-keyword list (brand.known_keywords). This
is what surfaces Content Gap candidates (a Semrush keyword with real
volume but no GSC/Ads/GA4 signal at all).

Phase "sample": reads data/sample/semrush_keywords_sample.json (Healing
Village only -- other brands aren't fixtured yet, return {}).

Phase "live": exact-match lookup (`phrase_this`, via
fetchers/semrush_client.py::fetch_phrase_overview_multi_db) for every
keyword in brand.known_keywords, across config.SEMRUSH_SEARCH_DATABASES.
Confirmed working on this account this session -- unlike `phrase_related`
(bulk discovery), which 403s on this account's plan, `phrase_this` returns
real data. A miss for one keyword doesn't block the rest.
"""
import os

import config
from fetchers import semrush_client
from fetchers._util import load_sample


def _fetch_live(brand):
    api_key = os.environ.get("SEMRUSH_API_KEY")
    if not api_key:
        raise RuntimeError(
            "SEMRUSH_API_KEY is not set -- Semrush live fetch cannot run. "
            "See module docstring / .env.example for where to find this key."
        )
    # DIAGNOSTIC (temporary): fetch_phrase_overview_multi_db swallows every
    # per-database exception silently by design (a miss is normal), which
    # makes a *systemic* failure (e.g. account API-unit exhaustion) look
    # identical to "no data for any keyword" with no way to tell them
    # apart from the caller's output alone. Surface the raw error for just
    # the first keyword/database so a real failure is visible in the
    # GitHub Actions log instead of silently producing zero entries.
    try:
        sample_row = semrush_client.fetch_phrase_overview(
            brand.known_keywords[0], api_key, database=config.SEMRUSH_SEARCH_DATABASES[0]
        )
        print(f"[fetch_semrush diagnostic] '{brand.known_keywords[0]}' ({config.SEMRUSH_SEARCH_DATABASES[0]}): {sample_row}")
    except Exception as exc:
        print(f"[fetch_semrush diagnostic] '{brand.known_keywords[0]}' ({config.SEMRUSH_SEARCH_DATABASES[0]}) FAILED: {exc}")

    result = {}
    for keyword in brand.known_keywords:
        overview = semrush_client.fetch_phrase_overview_multi_db(keyword, api_key, config.SEMRUSH_SEARCH_DATABASES)
        if overview:
            result[keyword] = overview
    return result


def fetch(phase, brand):
    if phase == "live":
        return _fetch_live(brand)
    if brand.key == "healing_village":
        return load_sample("semrush_keywords_sample.json")
    return {}
