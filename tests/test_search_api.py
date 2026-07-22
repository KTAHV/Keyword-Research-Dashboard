import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Make sure leftover credentials from the dev shell don't turn these into
# live-network tests.
for _var in (
    "ANTHROPIC_API_KEY", "SEMRUSH_API_KEY", "GOOGLE_ADS_CLIENT_ID",
    "GOOGLE_ADS_CLIENT_SECRET", "GSC_REFRESH_TOKEN", "GA4_REFRESH_TOKEN",
    "GOOGLE_ADS_REFRESH_TOKEN", "GOOGLE_ADS_DEVELOPER_TOKEN", "GOOGLE_ADS_LOGIN_CUSTOMER_ID",
):
    os.environ.pop(_var, None)

import config  # noqa: E402
from api.search import _demo_semrush_lookup, _is_systemic_failure, _seed_variants, run_search  # noqa: E402

HV = config.BRANDS["healing_village"]


def test_demo_lookup_matches_on_word_overlap_not_just_substring():
    # Regression test: "kairali ayurvedic" is not a substring of any sample
    # keyword (none contain "kairali"), but it shares "ayurvedic" with many
    # of them -- the reported bug was that this returned zero results.
    matches = _demo_semrush_lookup(["kairali ayurvedic"], HV)
    assert len(matches) > 0
    assert any("ayurvedic" in kw for kw in matches)


def test_demo_lookup_empty_for_truly_unrelated_seed():
    matches = _demo_semrush_lookup(["xyzunmatchedkeyword123"], HV)
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


def test_run_search_entries_carry_search_volume_and_source():
    result = run_search({"seedKeyword": "panchakarma"})
    assert result["entries"], "expected at least one entry"
    for e in result["entries"]:
        assert "searchVolume" in e
        assert e["volumeSource"] in ("Demo data", "No volume data")
    # The demo lookup's word-overlap match against the sample universe
    # should find at least one real "Demo data" entry for this seed.
    assert any(e["volumeSource"] == "Demo data" for e in result["entries"])


def test_run_search_no_live_google_cross_reference_without_credentials():
    result = run_search({"seedKeyword": "panchakarma"})
    assert result["liveGoogleCrossReference"] is False


def test_run_search_excludes_patient_nationality_pattern_from_results():
    # Broad seed that word-overlap-matches sample keywords containing the
    # "... for uk/german/dubai patients" pattern -- none should survive
    # into the final entries, even though they're topically related.
    result = run_search({"seedKeyword": "ayurveda treatment kerala"})
    leaked = [e["keyword"] for e in result["entries"] if "patient" in e["keyword"]]
    assert leaked == []
    assert any("compliance" in w.lower() for w in result["warnings"])


def test_run_search_sorted_by_priority_then_volume():
    result = run_search({"seedKeyword": "ayurveda treatment kerala"})
    priority_rank = {"High": 0, "Medium": 1, "Low": 2}
    ranks = [priority_rank[e["priority"]] for e in result["entries"]]
    assert ranks == sorted(ranks)


def test_seed_variants_drops_one_word_at_a_time():
    # Regression: Semrush's phrase_related can return NOTHING FOUND for a
    # specific 3-word phrase ("ayurveda treatment kerala") while a 2-word
    # subset of it ("ayurveda kerala") has real data -- confirmed live.
    # Every single-word-drop variant must be offered as a retry, not just
    # the trailing-word-dropped one.
    variants = _seed_variants("ayurveda treatment kerala")
    assert "ayurveda kerala" in variants
    assert "treatment kerala" in variants
    assert "ayurveda treatment" in variants


def test_seed_variants_empty_for_single_word():
    assert _seed_variants("panchakarma") == []


def test_is_systemic_failure_detects_collapsed_all_database_error():
    # Regression: a 403 (this Semrush plan doesn't include Related
    # Keywords) hits every database identically -- fetch_related_keywords_
    # multi_db collapses that into one short, non-technical line; the
    # caller should recognize it and stop retrying seed variants instead
    # of repeating the same doomed request four more times.
    assert _is_systemic_failure(
        ["Semrush's Related Keywords (bulk discovery) report isn't available for this account/plan -- showing exact-match keyword pricing only where available."]
    )


def test_is_systemic_failure_false_for_per_database_errors():
    assert not _is_systemic_failure(
        ["Semrush related-keywords lookup failed for database 'in': some transient error"]
    )
    assert not _is_systemic_failure([])


def test_run_search_blocks_restricted_seed_term_with_policy_notice():
    # Ayurvedic Healing Village's restricted-keyword policy (Google Ads /
    # tax / medical-claims compliance) -- a seed matching it must never be
    # searched directly; the response should explain why and still return
    # real fallback suggestions instead of an empty result.
    result = run_search({"seedKeyword": "ayurveda resort kerala"})
    assert result["policyNotice"] is not None
    assert "resort" in result["policyNotice"]
    assert "ayurveda resort kerala" not in result["resolvedSeeds"]
    assert result["entries"], "expected fallback suggestions instead of zero results"


def test_run_search_no_policy_notice_for_clean_seed():
    result = run_search({"seedKeyword": "panchakarma"})
    assert result.get("policyNotice") is None


def test_run_search_defaults_to_healing_village_when_brand_omitted():
    result = run_search({"seedKeyword": "panchakarma"})
    assert result["brand"] == "healing_village"


def test_run_search_villaraag_does_not_block_spa_wellness_terms():
    # Opposite of Healing Village: "spa"/"wellness" are legitimate product
    # terms for Villaraag, not a restricted-policy match.
    result = run_search({"brand": "villaraag", "seedKeyword": "spa and wellness villa goa"})
    assert result["brand"] == "villaraag"
    assert result.get("policyNotice") is None


def test_run_search_villaraag_blocks_explicit_content_terms():
    result = run_search({"brand": "villaraag", "seedKeyword": "escort service goa villa"})
    assert result["policyNotice"] is not None
    assert "escort" in result["policyNotice"]


def test_run_search_excludes_restricted_term_from_discovered_matches():
    # A restricted term can also arrive via discovery (Semrush phrase_
    # related, demo word-overlap) rather than the typed seed itself -- the
    # second compliance pass must catch that too, not just the seed check.
    with patch(
        "api.search._demo_semrush_lookup",
        return_value={
            "panchakarma treatment kerala": {"volumeByCountry": {"in": 100}, "cpc": None, "difficulty": None},
            "panchakarma resort kerala": {"volumeByCountry": {"in": 50}, "cpc": None, "difficulty": None},
        },
    ):
        result = run_search({"seedKeyword": "panchakarma"})
    leaked = [e["keyword"] for e in result["entries"] if "resort" in e["keyword"]]
    assert leaked == []
