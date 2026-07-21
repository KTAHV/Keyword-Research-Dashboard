"""
One-time script: run the OAuth2 installed-app flow and save a GSC-scoped
token file for this repo's live fetchers.

Usage:
    1. Copy credentials.json (the shared OAuth client -- same one used by
       the Combined Marketing Dashboard family, Google Cloud project
       "erudite-coast-502112-n5") into this repo's root. Never commit it
       (already in .gitignore).
    2. python scripts/authenticate_gsc.py
    3. A browser window opens -- log in as seo@ktahv.com and grant consent.
    4. token_gsc.json is written to the repo root (already in .gitignore).
       Copy its "refresh_token" value into GSC_REFRESH_TOKEN as a GitHub
       Actions secret; keep the file itself only for local --phase live runs.
"""
import json
import os

from google_auth_oauthlib.flow import InstalledAppFlow

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_PATH = os.path.join(ROOT, "credentials.json")
TOKEN_PATH = os.path.join(ROOT, "token_gsc.json")

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]


def main():
    if not os.path.exists(CREDENTIALS_PATH):
        raise SystemExit(
            f"{CREDENTIALS_PATH} not found -- copy it from an existing sibling "
            "dashboard folder (e.g. Combined Marketing Dashboard\\GSC Dashboard\\"
            "credentials.json) first. See this script's module docstring."
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
    print("Copy this value into the GSC_REFRESH_TOKEN GitHub Actions secret:")
    print(credentials.refresh_token)


if __name__ == "__main__":
    main()
