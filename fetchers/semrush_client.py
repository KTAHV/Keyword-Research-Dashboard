"""
Thin wrapper around Semrush's classic Analytics REST API
(https://api.semrush.com/) for the live Search tool (api/search.py). Kept
separate from fetchers/fetch_semrush.py, which serves the weekly *batch*
build from a fixed known-keyword list -- this module is for open-ended,
on-demand phrase discovery, a different shape of call.

Semrush returns semicolon-delimited text, not JSON, and reports errors as a
plain "ERROR NN :: message" response body with HTTP 200 -- both are handled
here so callers only ever see either a clean list of dicts or a raised
RuntimeError with Semrush's own message.
"""
import csv
import io

import requests

BASE_URL = "https://api.semrush.com/"
TIMEOUT = 10


def _run_report(report_type, phrase, api_key, database, export_columns, display_limit=None):
    params = {
        "type": report_type,
        "key": api_key,
        "phrase": phrase,
        "database": database,
        "export_columns": export_columns,
    }
    if display_limit:
        params["display_limit"] = display_limit

    resp = requests.get(BASE_URL, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    text = resp.text.strip()

    if text.startswith("ERROR"):
        raise RuntimeError(f"Semrush API error for '{phrase}': {text}")

    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    return list(reader)


def fetch_phrase_overview(phrase, api_key, database="in"):
    """The seed phrase's own volume/CPC/difficulty. Returns None if Semrush
    has no data for it (a brand-new/very-long-tail phrase)."""
    rows = _run_report("phrase_this", phrase, api_key, database, "Ph,Nq,Cp,Kd")
    if not rows:
        return None
    row = rows[0]
    return {
        "keyword": row.get("Phrase", phrase),
        "volume": int(row.get("Search Volume", 0) or 0),
        "cpc": round(float(row.get("CPC", 0) or 0) * 100),  # dollars -> cents, matches sample-fixture units
        "difficulty": round(float(row.get("Keyword Difficulty Index", 0) or 0)),
    }


def fetch_related_keywords(phrase, api_key, database="in", limit=15):
    """Related/expansion keywords for a seed phrase."""
    rows = _run_report("phrase_related", phrase, api_key, database, "Ph,Nq,Cp,Kd", display_limit=limit)
    results = []
    for row in rows:
        results.append({
            "keyword": row.get("Phrase", "").strip(),
            "volume": int(row.get("Search Volume", 0) or 0),
            "cpc": round(float(row.get("CPC", 0) or 0) * 100),
            "difficulty": round(float(row.get("Keyword Difficulty Index", 0) or 0)),
        })
    return [r for r in results if r["keyword"]]


def fetch_related_keywords_multi_db(phrase, api_key, databases, limit=30):
    """Discovery, not exact-match: calls fetch_related_keywords once per
    database and merges into one dict keyed by keyword, with per-database
    volume kept in volumeByCountry. This is the primary live candidate
    source for the Search tool (see api/search.py) -- phrase_related
    reliably returns real, volume-backed keywords for a broad seed, unlike
    phrase_this's exact-match lookup (confirmed empirically: phrase_this on
    an AI-brainstormed long-tail phrase returns "NOTHING FOUND" in every
    database far more often than not). A failure on one database doesn't
    block the others."""
    merged = {}
    errors = []
    for db in databases:
        try:
            rows = fetch_related_keywords(phrase, api_key, database=db, limit=limit)
        except Exception as exc:
            errors.append(f"Semrush related-keywords lookup failed for database '{db}': {exc}")
            continue
        for row in rows:
            entry = merged.setdefault(row["keyword"], {"volumeByCountry": {}, "cpc": None, "difficulty": None})
            if row["volume"] > 0:
                entry["volumeByCountry"][db] = row["volume"]
            if entry["cpc"] is None and row["cpc"]:
                entry["cpc"] = row["cpc"]
            if entry["difficulty"] is None and row["difficulty"] is not None:
                entry["difficulty"] = row["difficulty"]
    # drop anything that ended up with no volume in any database
    merged = {k: v for k, v in merged.items() if v["volumeByCountry"]}
    return merged, errors


def fetch_phrase_overview_multi_db(phrase, api_key, databases):
    """Exact-match overview across multiple databases -- used as a bonus
    enrichment for AI-suggested keywords (a miss here is expected and
    ignored, not an error; see api/search.py)."""
    volume_by_country = {}
    cpc = None
    difficulty = None
    for db in databases:
        try:
            overview = fetch_phrase_overview(phrase, api_key, database=db)
        except Exception:
            continue
        if overview and overview["volume"] > 0:
            volume_by_country[db] = overview["volume"]
            if cpc is None:
                cpc = overview["cpc"]
            if difficulty is None:
                difficulty = overview["difficulty"]
    if not volume_by_country:
        return None
    return {"volumeByCountry": volume_by_country, "cpc": cpc, "difficulty": difficulty}
