"""
GA4: sessions/engagement-rate/conversions/avg-engagement-time attributed to
each query (joined via landing page + GSC query in the live version).

Phase "sample": reads data/sample/ga4_engagement_sample.json.

Phase "live" (future): GA4 Data API `runReport` with dimension "sessionQuery"
or manual query on landing page, keyed by page id, same AuthorizedSession
pattern as Combined Marketing Dashboard/GA4 Dashboard/fetch_ga4_data.py. Key
events are book_now/PPC_Thanks/generate_lead/enquiry_form (same as Page
Quality Dashboard's config.KEY_EVENTS). Needs GA4_REFRESH_TOKEN.
"""
from fetchers._util import load_sample


def fetch(phase="sample"):
    if phase == "live":
        raise NotImplementedError(
            "Live GA4 Data API fetch needs GA4_REFRESH_TOKEN (see module "
            "docstring) -- not wired up yet."
        )
    return load_sample("ga4_engagement_sample.json")
