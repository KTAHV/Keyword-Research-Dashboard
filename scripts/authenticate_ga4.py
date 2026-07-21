"""
One-time script: run the OAuth2 installed-app flow and save a GA4-scoped
token file for this repo's live fetchers.

Same credentials.json (shared OAuth client) as authenticate_gsc.py -- see
that script's module docstring for setup steps. This one requests the
analytics.readonly scope instead and writes token_ga4.json.

Usage: python scripts/authenticate_ga4.py
Then copy the printed refresh_token into the GA4_REFRESH_TOKEN GitHub
Actions secret.
"""
import json
import os

from google_auth_oauthlib.flow import InstalledAppFlow

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_PATH = os.path.join(ROOT, "credentials.json")
TOKEN_PATH = os.path.join(ROOT, "token_ga4.json")

SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]


def main():
    if not os.path.exists(CREDENTIALS_PATH):
        raise SystemExit(
            f"{CREDENTIALS_PATH} not found -- copy it from an existing sibling "
            "dashboard folder first. See authenticate_gsc.py's module docstring."
        )

    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, scopes=SCOPES)
    credentials = flow.run_local_server(port=0)

    token_data = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
    }
    with open(TOKEN_PATH, "w", encoding="utf-8") as f:
        json.dump(token_data, f, indent=2)

    print(f"\nSaved {TOKEN_PATH}")
    print("Copy this value into the GA4_REFRESH_TOKEN GitHub Actions secret:")
    print(credentials.refresh_token)


if __name__ == "__main__":
    main()
