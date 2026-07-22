"""
Google Suggest / Autocomplete substitute.

Real-time Google Autocomplete has no official API. Ahrefs' "Search
Suggestions" endpoint (which does mirror actual Autocomplete data) was
tested live against the connected account during this project's planning
and returned "Insufficient plan" -- not usable at the current plan tier.

Per an explicit user decision, this fetcher instead approximates trending/
question phrases from Semrush's related-terms + question data (seed topic ->
list of suggested/question phrases, with a "trending" subset). This is
clearly weaker than real Autocomplete (it reflects Semrush's keyword
database refresh cadence, not what Google is suggesting right now) -- every
place this data surfaces in the dashboard must label it as an approximation,
never as literal Autocomplete.

Phase "sample": reads data/sample/google_suggest_proxy_sample.json
(Healing Village only -- other brands get {}).

Phase "live" (future): Semrush related_keywords / questions endpoints,
grouped by seed topic, same SEMRUSH_API_KEY as fetch_semrush.py -- not
wired up yet for any brand, so this returns {} rather than crashing the
weekly build (same graceful-degradation pattern used elsewhere in this
repo for not-yet-available data sources; the "trending phrase" flag just
defaults False everywhere until it is). If Ahrefs' plan is ever upgraded,
prefer swapping this fetcher to Ahrefs' keywords-explorer-search-suggestions
endpoint instead, since that is real Autocomplete data.
"""
from fetchers._util import load_sample


def fetch(phase, brand):
    if phase == "live":
        return {}
    if brand.key == "healing_village":
        data = load_sample("google_suggest_proxy_sample.json")
        data.pop("_note", None)
        return data
    return {}
