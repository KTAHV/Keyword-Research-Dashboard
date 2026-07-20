"""
Tier-A competitor keyword gap: keywords a Tier-A competitor
(config.TIER_A_COMPETITORS) ranks for that we don't, or ranks meaningfully
ahead of us on.

Phase "sample": reads data/sample/competitor_keywords_sample.json.

Phase "live" (future): Semrush `domain_organic_keywords` for each Tier-A
competitor's domain, diffed against our own GSC ranking set. Same
SEMRUSH_API_KEY as fetch_semrush.py.
"""
import os

from fetchers._util import load_sample


def fetch(phase="sample"):
    if phase == "live":
        if not os.environ.get("SEMRUSH_API_KEY"):
            raise RuntimeError(
                "SEMRUSH_API_KEY is not set -- competitor keyword gap live fetch "
                "cannot run. See module docstring / .env.example."
            )
        raise NotImplementedError(
            "Live Semrush competitor-keyword-gap fetch is not wired up yet (see module docstring)."
        )
    return load_sample("competitor_keywords_sample.json")
