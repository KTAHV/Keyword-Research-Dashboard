import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Make sure a leftover ANTHROPIC_API_KEY / SEMRUSH_API_KEY from the dev shell
# doesn't turn these into live-network tests.
os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ.pop("SEMRUSH_API_KEY", None)

from api.search import _demo_semrush_lookup, run_search  # noqa: E402


def test_demo_lookup_matches_on_word_overlap_not_just_substring():
    # Regression test: "kairali ayurvedic" is not a substring of any sample
    # keyword (none contain "kairali"), but it shares "ayurvedic" with many
    # of them -- the reported bug was that this returned zero results.
    matches = _demo_semrush_lookup(["kairali ayurvedic"])
    assert len(matches) > 0
    assert any("ayurvedic" in kw for kw in matches)


def test_demo_lookup_empty_for_truly_unrelated_seed():
    matches = _demo_semrush_lookup(["xyzunmatchedkeyword123"])
    assert matches == {}


def test_run_search_falls_back_to_basic_ideation_without_anthropic_key():
    result = run_search({"seedKeyword": "panchakarma"})
    assert result["ideation"] == "basic"
    assert result["mode"] == "demo"
    assert len(result["entries"]) > 0
    assert any("priority" in e for e in result["entries"])


def test_run_search_requires_at_least_one_input():
    result = run_search({})
    assert "error" in result
