"""
Materializes token_gsc.json, token_ga4.json, and google-ads.yaml from
environment variables, right before the fetchers that need them run.
Nothing here is ever committed -- all three output files are in
.gitignore.

Two callers:
- CLI (`python scripts/write_credentials.py`, __main__ below): GitHub
  Actions, writes to the repo root, right before
  build_keyword_research_dashboard.py --phase live
  (.github/workflows/weekly_refresh.yml).
- api/search.py, importing materialize_all(output_dir=...) directly:
  Vercel's filesystem is read-only except /tmp, so the live Search tool
  materializes into /tmp at request time instead, then points
  TOKEN_GSC_PATH/TOKEN_GA4_PATH/GOOGLE_ADS_YAML_PATH at the /tmp files
  (see fetchers/fetch_gsc.py, fetch_ga4.py, fetchers/ads_client.py's
  overridable path functions).

Mirrors the sibling Combined Marketing Dashboard repo's
scripts/write_credentials.py -- GSC and GA4 reuse the same shared OAuth
client (GOOGLE_ADS_CLIENT_ID/SECRET), only their refresh tokens differ.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OAUTH_TOKEN_URI = "https://oauth2.googleapis.com/token"


def write_token_file(output_dir, filename, refresh_token, scopes, client_id, client_secret):
    path = os.path.join(output_dir, filename)
    data = {
        "token": "",  # populated by Credentials.refresh() at fetch time
        "refresh_token": refresh_token,
        "token_uri": OAUTH_TOKEN_URI,
        "client_id": client_id,
        "client_secret": client_secret,
        "scopes": scopes,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return path


def write_ads_yaml(output_dir, client_id, client_secret, developer_token, refresh_token, login_customer_id):
    path = os.path.join(output_dir, "google-ads.yaml")
    lines = [
        f'developer_token: "{developer_token}"',
        f'client_id: "{client_id}"',
        f'client_secret: "{client_secret}"',
        f'refresh_token: "{refresh_token}"',
        f'login_customer_id: "{login_customer_id}"',
        "use_proto_plus: True",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path


def materialize_all(output_dir=ROOT, env=None):
    """Reads credentials from `env` (defaults to os.environ) and writes
    whichever of token_gsc.json/token_ga4.json/google-ads.yaml have all
    their required env vars set. Returns a dict of the paths actually
    written (keys: "gsc", "ga4", "ads" -- only present if written), so
    callers can point the fetchers' path overrides at them."""
    env = env if env is not None else os.environ
    written = {}

    client_id = env.get("GOOGLE_ADS_CLIENT_ID")
    client_secret = env.get("GOOGLE_ADS_CLIENT_SECRET")
    if not client_id or not client_secret:
        return written  # shared client -- nothing else can be written without it

    gsc_refresh_token = env.get("GSC_REFRESH_TOKEN")
    if gsc_refresh_token:
        written["gsc"] = write_token_file(
            output_dir, "token_gsc.json", gsc_refresh_token,
            ["https://www.googleapis.com/auth/webmasters.readonly"],
            client_id, client_secret,
        )

    ga4_refresh_token = env.get("GA4_REFRESH_TOKEN")
    if ga4_refresh_token:
        written["ga4"] = write_token_file(
            output_dir, "token_ga4.json", ga4_refresh_token,
            ["https://www.googleapis.com/auth/analytics.readonly"],
            client_id, client_secret,
        )

    ads_refresh_token = env.get("GOOGLE_ADS_REFRESH_TOKEN")
    developer_token = env.get("GOOGLE_ADS_DEVELOPER_TOKEN")
    login_customer_id = env.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID")
    if ads_refresh_token and developer_token and login_customer_id:
        written["ads"] = write_ads_yaml(
            output_dir, client_id, client_secret, developer_token,
            ads_refresh_token, login_customer_id,
        )

    return written


def main():
    written = materialize_all()
    for source in ("gsc", "ga4", "ads"):
        if source in written:
            print(f"Wrote {written[source]}")
        else:
            print(f"{source}: required env vars not set -- skipped")


if __name__ == "__main__":
    main()
