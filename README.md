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
Then open `http://localhost:8000/` (built as `index.html` so Vercel serves
it at the domain root with no output-directory config needed).

## Phase 1 (current, sample data) vs Phase 2 (live)

Runs entirely against `data/sample/*.json` fixtures shaped like the real
fetcher output. The merge/scoring/HTML-generation code never changes between
phases — only `--phase sample` vs `--phase live`.

Three things are needed before Phase 2 works — status as of this README:

1. **`SEMRUSH_API_KEY`** — done, set in both GitHub Actions secrets and Vercel.
2. **`ANTHROPIC_API_KEY`** — done, set in Vercel (only needed by the live
   Search tool, see below — not by the weekly batch).
3. **Fresh GSC / GA4 / Google Ads credentials**, scoped to this standalone
   repo's own GitHub Actions secrets (not reused from the Combined Marketing
   Dashboard repo) — **done**, see below.

### GSC / GA4 / Google Ads — one-time OAuth setup

`fetchers/fetch_gsc.py`, `fetch_ga4.py`, and `fetch_google_ads_search_terms.py`
mirror the sibling Combined Marketing Dashboard family's exact live patterns
(raw REST `searchAnalytics.query` for GSC, `BetaAnalyticsDataClient` for
GA4, `GoogleAdsClient` GAQL for Ads), targeting the same Kairali accounts:
GA4 property `394301498`, GSC sites `ayurvedichealingvillage.com` (both the
apex and `www.` variants), Ads customer `7129610573` under MCC `9230793935`.
All three reuse the same shared Google Cloud OAuth client (project
`erudite-coast-502112-n5`) the sibling dashboards already use — but this
repo gets its **own, fresh refresh tokens**, not copies of the siblings'.

1. Copy `credentials.json` from an existing sibling dashboard folder (e.g.
   `Combined Marketing Dashboard\GSC Dashboard\credentials.json`) into this
   repo's root. Never commit it — already in `.gitignore`.
2. Run `scripts/authenticate_all.py` locally — one browser window opens,
   requesting the GSC + GA4 + Ads scopes together in a single consent grant
   (log in as `seo@ktahv.com`): writes `token_gsc.json` + `token_ga4.json`
   and prints the one refresh token to use for `GOOGLE_ADS_REFRESH_TOKEN`
   too (Ads has no token file of its own — it lives in `google-ads.yaml`,
   see `fetch_google_ads_search_terms.py`).
3. Add these as GitHub Actions repo secrets (Settings → Secrets and
   variables → Actions): `GOOGLE_ADS_CLIENT_ID`, `GOOGLE_ADS_CLIENT_SECRET`
   (both from `credentials.json`), `GOOGLE_ADS_DEVELOPER_TOKEN`,
   `GOOGLE_ADS_LOGIN_CUSTOMER_ID` (`9230793935`), `GOOGLE_ADS_REFRESH_TOKEN`,
   `GA4_REFRESH_TOKEN`, `GSC_REFRESH_TOKEN`. The weekly workflow's
   `scripts/write_credentials.py` step turns these into `token_gsc.json`,
   `token_ga4.json`, and `google-ads.yaml` at build time — nothing is ever
   committed.
4. **Vercel** (Project → Settings → Environment Variables) needs a subset of
   the same six: `GOOGLE_ADS_CLIENT_ID`, `GOOGLE_ADS_CLIENT_SECRET`,
   `GOOGLE_ADS_DEVELOPER_TOKEN`, `GOOGLE_ADS_LOGIN_CUSTOMER_ID`,
   `GOOGLE_ADS_REFRESH_TOKEN`, `GSC_REFRESH_TOKEN` — so the live Search tool
   can cross-reference GSC + Ads per search. **`GA4_REFRESH_TOKEN` is
   deliberately NOT set in Vercel** — GA4 has no native search-query
   dimension (only GSC does), so it's excluded entirely from the Search
   tool's live cross-referencing; GA4 stays weekly-batch/page-level only
   (see `api/search.py`'s module docstring).

## Search tool (live, on-demand) — the dashboard's default landing view

The homepage is now an interactive search tool, not the weekly batch report
(that moved to the **Weekly Report** sidebar tab — see below, nothing was
deleted). Type a seed keyword, paste a URL, or paste raw page content, hit
Search, and get a fresh priority-sorted keyword list.

Static HTML can't call Semrush/GSC/GA4/Ads directly -- API keys and OAuth
secrets can't safely live in browser JS, and most of these APIs block direct
browser calls anyway (CORS). The server-side half is a **Vercel Python
serverless function** at `api/search.py`, which Vercel deploys automatically
alongside the static site (no extra config needed -- the `api/` folder is a
zero-config convention). It reuses this repo's own `analysis/` scoring
modules via `analysis/entry_builder.py`, so the weekly batch and the live
search can never score a keyword differently.

- **Semrush** volume/CPC/difficulty comes from `phrase_related` (real
  discovery, not exact-match-only) on the seed, across every market in
  `config.SEMRUSH_SEARCH_DATABASES` (`in`, `us`, `uk`, `ae`) — plus a
  best-effort `phrase_this` exact lookup per AI-suggested candidate. If an
  AI-suggested candidate still has no volume after that, and Google Ads
  credentials are configured, **Google Keyword Planner**
  (`fetchers/keyword_planner_client.py`) is queried as a fallback so a
  seed rarely dead-ends with "nothing found".
- **GSC + Ads** are queried live per search (position/mapped-page from GSC,
  paid-verification signal from Ads) when Google credentials are set in
  Vercel — see the OAuth setup section above. **GA4 is not part of this
  live path** (no native search-query dimension); if a searched keyword
  happens to match one already in the last weekly-committed
  `data/keyword_research_data.json`, its cached GA4 signal is folded in
  instead. Otherwise GA4 is honestly shown as "no data yet" — never
  fabricated.
- **Compliance filter**: any candidate or discovered keyword that pairs
  "patient(s)" with a specific nationality/country name (e.g. "for uk
  patients", "for gulf patients") is excluded from results entirely, not
  just downranked — see `analysis/compliance.py::is_patient_nationality_pattern`.
- **Credentials**: `SEMRUSH_API_KEY` must be added in **two separate
  places**: GitHub Actions secrets (weekly cron, per above) *and*
  Vercel → Project → Settings → Environment Variables (for `api/search.py`
  at request time). Until the Vercel one is set, the tool runs in a clearly
  labelled **demo mode** (matches against the local sample keyword universe,
  via word-overlap so it still returns something useful, instead of calling
  Semrush), so the whole feature is testable end-to-end today.

### AI keyword ideation (Claude)

Rather than mechanically matching the typed seed against a keyword list, the
Search tool asks Claude (`analysis/ai_keyword_ideation.py`) to think like an
Ayurveda-hospital marketing expert about the seed/URL/pasted content and
propose 15-25 realistic candidate keywords — primary terms, long-tail
phrases, question variations, international-patient phrasing — before those
candidates go through this repo's own deterministic scoring pipeline
(`analysis/entry_builder.py`). Claude only *proposes keyword strings*; every
score (intent, compliance, AEO, confidence, ...) still comes from the same
auditable rule-based code the weekly batch uses, never from the model.

- **Model**: `claude-opus-4-8`, via the official `anthropic` Python SDK
  (structured output / Pydantic schema, not free-text parsing).
- **Credential**: `ANTHROPIC_API_KEY` — a **new, separate** credential from
  `SEMRUSH_API_KEY`, and separate from any Claude Code/Claude.ai
  subscription (this is pay-as-you-go Claude API billing). Get one at
  `https://console.anthropic.com/settings/keys`, then add it to Vercel →
  Project → Settings → Environment Variables. **Status: pending.**
- **Cost**: roughly $0.01–0.02 per search click at Opus rates. Without this
  key set, the tool falls back to a simpler regex-based keyword expansion —
  it still works, just without the expert-level understanding.
- **No auth on the endpoint**: `/api/search` has no login/rate-limit, so
  anyone who opens the dashboard and clicks Search triggers a (small) paid
  Claude call once this key is set. Worth knowing before enabling it on a
  public URL.

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
`index.html` straight back to this repo. Live runs will
fail loudly (not silently fall back to sample data) until `SEMRUSH_API_KEY`
and the Google credentials are set as repo secrets.

## Project layout

- `config.py` — domain, mapped pages (shared ids with Page Quality
  Dashboard), Tier-A competitors, country scope, exclusion/compliance/
  specificity vocabulary, scoring weights.
- `fetchers/` — one module per data source; `fetch(phase="sample"|"live")`.
  `semrush_client.py` is the raw Semrush REST wrapper used only by the live
  Search tool (open-ended discovery), separate from `fetch_semrush.py`
  (the weekly batch's fixed known-keyword refresh).
- `analysis/` — `intent_and_audience.py`, `ai_voice_readiness.py`,
  `compliance.py`, `competitor_and_gap.py`, `confidence.py`, `rules.py`
  (Needs Attention alert generation), `entry_builder.py` (shared keyword
  scoring/assembly used by both the batch build and `api/search.py`),
  `phrase_extraction.py` (regex-based fallback seed-phrase extraction),
  `ai_keyword_ideation.py` (Claude-based semantic keyword ideation, the
  preferred path when `ANTHROPIC_API_KEY` is set).
- `build_keyword_research_dashboard.py` — weekly-batch orchestrator.
- `api/search.py` — Vercel serverless function behind the live Search tool.
- `dashboard_html.py` — static HTML/CSS/JS template: sidebar (Search +
  Weekly Report + workspace items), hero banner, the Search tool's three
  inputs, and the Weekly Report's tier-tabbed KPI/keyword-list views.
- `data/sample/` — fixtures; `data/keyword_research_data.json` /
  `data/keyword_history.json` — weekly build output, also read at request
  time by `api/search.py` as a cached-GA4 / cross-reference fallback.
- `scripts/verify_build.py` — schema sanity check, no browser needed.
- `tests/test_scoring.py` — pytest for the analysis/scoring math.
