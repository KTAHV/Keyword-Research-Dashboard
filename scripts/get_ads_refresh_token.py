"""
One-time script: run the OAuth2 installed-app flow and print a Google-Ads-
scoped refresh token. Unlike GSC/GA4, Google Ads has no token*.json --
its credentials live in one google-ads.yaml file (see
fetchers/fetch_google_ads_search_terms.py), so this script only prints the
refresh token for you to paste in yourself.

Same credentials.json (shared OAuth client) as authenticate_gsc.py -- see
that script's module docstring for setup steps.

Usage: python scripts/get_ads_refresh_token.py
Then either:
  - paste the printed value into GOOGLE_ADS_REFRESH_TOKEN as a GitHub
    Actions secret (for CI, via scripts/write_credentials.py), or
  - paste it directly into a local google-ads.yaml for local --phase live
    runs (see fetch_google_ads_search_terms.py for the expected shape).
"""
import os

from google_auth_oauthlib.flow import InstalledAppFlow

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_PATH = os.path.join(ROOT, "credentials.json")

SCOPES = ["https://www.googleapis.com/auth/adwords"]


def main():
    if not os.path.exists(CREDENTIALS_PATH):
        raise SystemExit(
            f"{CREDENTIALS_PATH} not found -- copy it from an existing sibling "
            "dashboard folder first. See authenticate_gsc.py's module docstring."
        )

    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, scopes=SCOPES)
    credentials = flow.run_local_server(port=0)

    print("\nCopy this value into the GOOGLE_ADS_REFRESH_TOKEN GitHub Actions secret:")
    print(credentials.refresh_token)


if __name__ == "__main__":
    main()
