# Keyword Research Dashboard

Standalone keyword-research tool for `ayurvedichealingvillage.com` (Kairali
Ayurvedic Healing Village, NABH-accredited). Finds high-volume, genuine-
audience search terms across traditional SEO and AEO/GEO/AI-search, while
automatically excluding low-quality traffic (spa/massage/escort-seeking,
DIY/home-remedy, job-seekers). Fully independent from the Combined Marketing
Dashboard family — separate repo, separate Vercel project, not linked into
the master tri-tab landing page.

## Quick start

```
pip install -r requirements.txt
python build_keyword_research_dashboard.py        # --phase sample (default)
python scripts/verify_build.py
pytest tests/test_scoring.py -q
python -m http.server 8000
```
Then open `http://localhost:8000/keyword-research-dashboard.html`.

## Phase 1 (current, sample data) vs Phase 2 (live)

Runs entirely against `data/sample/*.json` fixtures shaped like the real
fetcher output. The merge/scoring/HTML-generation code never changes between
phases — only `--phase sample` vs `--phase live`.

Two things are needed before Phase 2 works:

1. **Fresh GSC / GA4 / Google Ads credentials**, scoped to this standalone
   repo's own GitHub Actions secrets (not reused from the Combined Marketing
   Dashboard repo — see `.env.example`).
2. **A Semrush REST API key** (`SEMRUSH_API_KEY`) — separate from the
   Semrush MCP connection used interactively in Claude Code, which cannot be
   called from a headless GitHub Actions script. Find it at semrush.com →
   profile menu → Subscription info →
   `https://www.semrush.com/subscription-info/api-units/`. **Status: pending**
   — not yet confirmed whether the current plan exposes one.

## Google Suggest / Autocomplete — approximated, not literal

There is no official Google Autocomplete API. Ahrefs' "Search Suggestions"
endpoint (which does mirror real Autocomplete data) was tested against the
connected account during planning and returned `"Insufficient plan"` — not
usable at the current tier. Per an explicit product decision, trending/
question-phrase data is instead approximated from Semrush's related-terms +
questions data (see `fetchers/fetch_google_suggest_proxy.py`). Every place
this surfaces in the dashboard is labelled as an approximation.

## Parameter groups — descriptive names only

Per an explicit decision (also applied to the sibling Page Quality
Dashboard), nothing is labelled "Tier 1/2/3…" anywhere — in code, data, or
UI. The six parameter groups are:

- **Core Search Metrics** — volume by country, competition, CPC, current
  ranking position, trending-phrase flag.
- **Audience Fit & Intent** — intent classification, Audience-Fit Score,
  spam-risk flag, Medical/Therapeutic Specificity Score.
- **AI & Voice Search Readiness** — AEO Score, Answerability Score, GEO
  Visibility Potential, Schema Readiness.
- **Compliance Check** — Medical/Health Compliance Risk, Google Ads
  Healthcare & Medicines Policy risk, YMYL Policy risk.
- **Competitor & Content Gap** — Tier-A competitor overlap/gap, keyword
  cannibalization, content-gap identification.
- **Cross-Source Confidence** — GSC + GA4 + Ads + Semrush combined
  Confidence Score, underperformance flag.

## Competitor scope

Same Tier-A list as Page Quality Dashboard's `config.TIER_A_COMPETITORS`:
Somatheeram Ayurveda Village, Kalari Kovilakom, Vaidyagrama, Neeleshwar
Hermitage, Kairali Heritage Resort.

## Refresh

`.github/workflows/weekly_refresh.yml` runs Monday mornings (08:00 IST) +
on-demand via `workflow_dispatch`, and commits the refreshed
`data/keyword_research_data.json`, `data/keyword_history.json`, and
`keyword-research-dashboard.html` straight back to this repo. Live runs will
fail loudly (not silently fall back to sample data) until `SEMRUSH_API_KEY`
and the Google credentials are set as repo secrets.

## Project layout

- `config.py` — domain, mapped pages (shared ids with Page Quality
  Dashboard), Tier-A competitors, country scope, exclusion/compliance/
  specificity vocabulary, scoring weights.
- `fetchers/` — one module per data source; `fetch(phase="sample"|"live")`.
- `analysis/` — `intent_and_audience.py`, `ai_voice_readiness.py`,
  `compliance.py`, `competitor_and_gap.py`, `confidence.py`, `rules.py`
  (Needs Attention alert generation).
- `build_keyword_research_dashboard.py` — orchestrator.
- `dashboard_html.py` — static HTML/CSS/JS template (sidebar, hero banner,
  KPI cards, two-panel Overview, per-section keyword tables).
- `data/sample/` — fixtures; `data/keyword_research_data.json` /
  `data/keyword_history.json` — build output.
- `scripts/verify_build.py` — schema sanity check, no browser needed.
- `tests/test_scoring.py` — pytest for the analysis/scoring math.
