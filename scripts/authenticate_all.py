"""
One-time script: run a SINGLE OAuth2 installed-app flow requesting the GSC +
GA4 + Ads scopes together (one browser consent screen, not three), and write
everything this repo's live fetchers need.

Same shared OAuth client as the sibling Combined Marketing Dashboard family
(project "erudite-coast-502112-n5") -- this repo gets its own fresh refresh
token, not a copy of a sibling's.

Usage:
    1. Copy credentials.json (the shared OAuth client) into this repo's
       root. Never commit it -- already in .gitignore.
    2. python scripts/authenticate_all.py
    3. A browser window opens once -- log in as seo@ktahv.com and grant
       consent for all three scopes on the one screen.
    4. token_gsc.json and token_ga4.json are written to the repo root
       (already in .gitignore). The same refresh token is also printed for
       GOOGLE_ADS_REFRESH_TOKEN -- Ads has no token file of its own, it
       lives in google-ads.yaml (see fetchers/fetch_google_ads_search_terms.py).
"""
import json
import os

from google_auth_oauthlib.flow import InstalledAppFlow

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_PATH = os.path.join(ROOT, "credentials.json")

SCOPES = [
    "https://www.googleapis.com/auth/webmasters.readonly",
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/adwords",
]


def _write_token_file(filename, credentials):
    path = os.path.join(ROOT, filename)
    token_data = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(token_data, f, indent=2)
    return path


def main():
    if not os.path.exists(CREDENTIALS_PATH):
        raise SystemExit(
            f"{CREDENTIALS_PATH} not found -- copy it from an existing sibling "
            "dashboard folder (e.g. Combined Marketing Dashboard\\GSC Dashboard\\"
            "credentials.json) first. See this script's module docstring."
        )

    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, scopes=SCOPES)
    credentials = flow.run_local_server(port=0)

    gsc_path = _write_token_file("token_gsc.json", credentials)
    ga4_path = _write_token_file("token_ga4.json", credentials)

    print(f"\nSaved {gsc_path}")
    print(f"Saved {ga4_path}")
    print("\nGSC_REFRESH_TOKEN / GA4_REFRESH_TOKEN / GOOGLE_ADS_REFRESH_TOKEN "
          "(same value for all three -- one combined grant):")
    print(credentials.refresh_token)


if __name__ == "__main__":
    main()
