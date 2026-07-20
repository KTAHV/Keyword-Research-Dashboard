"""
Google Search Console: per-query impressions/clicks/ctr/position, plus which
mapped page (if any) currently ranks for that query.

Phase "sample": reads data/sample/gsc_queries_sample.json.

Phase "live" (future): Search Analytics `searchanalytics.query` call,
dimensions=["query", "page"], same AuthorizedSession + refresh-token pattern
as Combined Marketing Dashboard/GSC Dashboard/fetch_url_health_cwv.py. Map
the returned page URL back to a config.PAGE_IDS entry (or None if it doesn't
match any of the 13 tracked pages -- that's a Content Gap candidate).
Needs GSC_REFRESH_TOKEN.
"""
from fetchers._util import load_sample


def fetch(phase="sample"):
    if phase == "live":
        raise NotImplementedError(
            "Live GSC searchanalytics.query fetch needs GSC_REFRESH_TOKEN "
            "(see module docstring) -- not wired up yet."
        )
    return load_sample("gsc_queries_sample.json")
