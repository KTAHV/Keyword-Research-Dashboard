"""
Tier-A competitor keyword gap: keywords a Tier-A competitor
(brand.tier_a_competitors) ranks for that we don't, or ranks meaningfully
ahead of us on.

Phase "sample": reads data/sample/competitor_keywords_sample.json
(Healing Village only -- brands with no sample fixture get {}).

Phase "live" (future): Semrush `domain_organic_keywords` for each Tier-A
competitor's domain, diffed against our own GSC ranking set -- not
implemented yet for any brand, so this returns {} rather than crashing
the weekly build (same graceful-degradation pattern used elsewhere in
this repo for not-yet-available data sources). Brands with no
tier_a_competitors configured at all (e.g. Villaraag, pending real rival
names) always return {} regardless of phase -- there's nothing to diff
against.
"""
from fetchers._util import load_sample


def fetch(phase, brand):
    if not brand.tier_a_competitors:
        return {}
    if phase == "live":
        return {}  # Semrush domain_organic_keywords not wired up yet -- Competitor Gap shows empty until it is
    if brand.key == "healing_village":
        return load_sample("competitor_keywords_sample.json")
    return {}
