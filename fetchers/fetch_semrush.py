"""
Semrush: the broad keyword universe -- volume by country, CPC, difficulty,
parent topic, and each keyword's own related-questions list. This is the
widest of the five sources and is what surfaces Content Gap candidates (a
Semrush keyword with real volume but no GSC/Ads/GA4 signal at all).

Phase "sample": reads data/sample/semrush_keywords_sample.json.

Phase "live" (future): Semrush REST API (keyword_overview /
keyword_difficulty / related_keywords endpoints), authenticated with
SEMRUSH_API_KEY -- a plain API key, distinct from the Semrush MCP connection
used interactively in Claude Code (MCP tools aren't callable from a headless
GitHub Actions script). As of this repo's creation SEMRUSH_API_KEY is
PENDING -- the user is checking semrush.com -> Subscription info ->
https://www.semrush.com/subscription-info/api-units/ for whether their plan
exposes one.
"""
import os

from fetchers._util import load_sample


def fetch(phase="sample"):
    if phase == "live":
        if not os.environ.get("SEMRUSH_API_KEY"):
            raise RuntimeError(
                "SEMRUSH_API_KEY is not set -- Semrush live fetch cannot run. "
                "See module docstring / .env.example for where to find this key."
            )
        raise NotImplementedError(
            "Live Semrush REST API fetch is not wired up yet (see module docstring)."
        )
    return load_sample("semrush_keywords_sample.json")
