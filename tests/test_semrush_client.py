import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fetchers import semrush_client  # noqa: E402


def test_run_report_http_error_never_includes_api_key():
    # Regression: requests' own HTTPError/RequestException messages embed
    # the full request URL, including "key=<the live Semrush API key>".
    # api/search.py surfaces exception text straight to the browser as a
    # warning, so that would leak the key to anyone who triggers this
    # path. _run_report must never let that string reach the caller.
    class FakeResponse:
        ok = False
        status_code = 403
        text = ""

    with patch("fetchers.semrush_client.requests.get", return_value=FakeResponse()):
        try:
            semrush_client._run_report(
                "phrase_related", "some phrase", "sk-super-secret-key-12345",
                "in", "Ph,Nq,Cp,Kd",
            )
            assert False, "expected RuntimeError"
        except RuntimeError as exc:
            assert "sk-super-secret-key-12345" not in str(exc)


def test_run_report_connection_error_never_includes_api_key():
    import requests

    with patch(
        "fetchers.semrush_client.requests.get",
        side_effect=requests.exceptions.ConnectionError(
            "Failed to resolve 'api.semrush.com' with key=sk-super-secret-key-12345"
        ),
    ):
        try:
            semrush_client._run_report(
                "phrase_related", "some phrase", "sk-super-secret-key-12345",
                "in", "Ph,Nq,Cp,Kd",
            )
            assert False, "expected RuntimeError"
        except RuntimeError as exc:
            assert "sk-super-secret-key-12345" not in str(exc)


def test_fetch_related_keywords_multi_db_collapses_identical_errors():
    # Regression: an HTTP 403 (Related Keywords not on this account's
    # plan) hits every database identically -- that should collapse into
    # one warning, not four near-duplicate lines.
    with patch(
        "fetchers.semrush_client.fetch_related_keywords",
        side_effect=RuntimeError("Semrush API HTTP 403 for report 'phrase_related'"),
    ):
        merged, errors = semrush_client.fetch_related_keywords_multi_db(
            "seed", "key", ["in", "us", "uk", "ae"]
        )
    assert merged == {}
    assert len(errors) == 1
    assert "every configured database" in errors[0]


def test_fetch_related_keywords_multi_db_keeps_distinct_errors_separate():
    calls = {"in": RuntimeError("boom in"), "us": RuntimeError("boom us")}

    def fake_fetch(phrase, api_key, database="in", limit=15):
        raise calls[database]

    with patch("fetchers.semrush_client.fetch_related_keywords", side_effect=fake_fetch):
        merged, errors = semrush_client.fetch_related_keywords_multi_db(
            "seed", "key", ["in", "us"]
        )
    assert merged == {}
    assert len(errors) == 2
