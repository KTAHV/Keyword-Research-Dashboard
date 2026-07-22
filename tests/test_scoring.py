import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
from analysis import ai_voice_readiness, competitor_and_gap, compliance, confidence, intent_and_audience  # noqa: E402
from analysis import ai_keyword_ideation, entry_builder, phrase_extraction  # noqa: E402

HV = config.BRANDS["healing_village"]
VR = config.BRANDS["villaraag"]


def test_spam_risk_flag():
    assert intent_and_audience.spam_risk_flag("ayurvedic massage near me", HV) == "Flagged"
    assert intent_and_audience.spam_risk_flag("panchakarma treatment kerala", HV) == "None"


def test_spam_risk_flag_differs_by_brand():
    # "spa"/"massage"/"wellness" are legitimate product terms for a leisure
    # resort (Villaraag) but spam-adjacent for a hospital (Healing Village)
    # -- same keyword, different brand, different verdict.
    assert intent_and_audience.spam_risk_flag("spa and wellness villa goa", VR) == "None"
    assert intent_and_audience.spam_risk_flag("ayurvedic massage near me", HV) == "Flagged"


def test_classify_intent_low_quality():
    assert intent_and_audience.classify_intent("ayurvedic massage near me", HV) == "Low-Quality"
    assert intent_and_audience.classify_intent("ayurveda home remedies for weight loss", HV) == "Low-Quality"
    assert intent_and_audience.classify_intent("ayurveda hospital jobs kerala", HV) == "Low-Quality"


def test_classify_intent_informational_question():
    assert intent_and_audience.classify_intent("what is panchakarma treatment", HV) == "Informational"


def test_classify_intent_commercial():
    assert intent_and_audience.classify_intent("panchakarma treatment kerala", HV) == "Commercial"
    assert intent_and_audience.classify_intent("private pool villa goa", VR) == "Commercial"


def test_audience_fit_score_bands():
    high = intent_and_audience.audience_fit_score(
        "best ayurveda hospital kerala", {"in": 3600, "us": 410, "uk": 260, "ae": 520}, 158, HV
    )
    assert high == "High"
    spam = intent_and_audience.audience_fit_score("ayurvedic massage near me", {"in": 8100}, 39, HV)
    assert spam == "Low"


def test_aeo_and_answerability_reward_questions():
    q_score = ai_voice_readiness.aeo_score("what is panchakarma treatment")
    non_q_score = ai_voice_readiness.aeo_score("panchakarma treatment kerala")
    assert q_score > non_q_score


def test_schema_readiness():
    assert ai_voice_readiness.schema_readiness("how to choose a genuine ayurveda hospital") == "HowTo Schema"
    assert ai_voice_readiness.schema_readiness("what is panchakarma treatment") == "FAQ Schema"
    assert ai_voice_readiness.schema_readiness("panchakarma treatment kerala") == "None"


def test_compliance_check_flags_claim_language():
    result = compliance.compliance_check("guaranteed cure for chronic pain ayurveda", HV)
    assert result["overallRisk"] == "High"
    assert "cure" in result["flaggedTerms"]

    clean = compliance.compliance_check("panchakarma treatment kerala", HV)
    assert clean["overallRisk"] == "Low"
    assert clean["flaggedTerms"] == []


def test_compliance_check_medical_claims_not_applicable_for_villaraag():
    # Villaraag has medical_compliance_enabled=False -- "cure"/"guaranteed"
    # language isn't even in its compliance_risk_terms, so this must not
    # trigger the medical-claim branch at all.
    result = compliance.compliance_check("guaranteed cure for chronic pain", VR)
    assert result["overallRisk"] == "Low"


def test_compliance_check_restricted_terms_apply_for_villaraag():
    result = compliance.compliance_check("escort service near villa", VR)
    assert result["overallRisk"] == "High"


def test_confidence_combines_available_sources():
    gsc = {"impressions": 4800, "clicks": 310, "ctr": 6.5, "position": 4.2}
    ga4 = {"sessions": 290, "engagementRate": 68.4, "conversions": 22}
    ads = {"impressions": 2100, "clicks": 165, "cost": 24850, "conversions": 14}
    score, subs = confidence.compute_confidence(gsc, ga4, ads, {"in": 2900, "us": 320}, 38)
    assert 0 <= score <= 100
    assert subs["gsc"] is not None and subs["ga4"] is not None and subs["ads"] is not None

    score_no_ads, subs_no_ads = confidence.compute_confidence(gsc, ga4, None, {"in": 2900}, 38)
    assert subs_no_ads["ads"] is None
    assert 0 <= score_no_ads <= 100


def test_underperformance_flag():
    good_rank_low_engagement = confidence.underperformance_flag(
        {"position": 3.5}, {"engagementRate": 22.1}
    )
    assert good_rank_low_engagement is True

    good_rank_good_engagement = confidence.underperformance_flag(
        {"position": 4.2}, {"engagementRate": 68.4}
    )
    assert good_rank_good_engagement is False

    no_gsc = confidence.underperformance_flag(None, {"engagementRate": 10})
    assert no_gsc is False


def test_content_gap_candidate():
    unmapped_clean = {
        "mappedPageId": None, "intent": "Commercial", "complianceRisk": "Low", "competitorGap": None,
    }
    assert competitor_and_gap.is_content_gap_candidate(unmapped_clean) is True

    mapped = dict(unmapped_clean, mappedPageId="panchakarma-treatment")
    assert competitor_and_gap.is_content_gap_candidate(mapped) is False

    spam = dict(unmapped_clean, intent="Low-Quality")
    assert competitor_and_gap.is_content_gap_candidate(spam) is False

    high_risk = dict(unmapped_clean, complianceRisk="High")
    assert competitor_and_gap.is_content_gap_candidate(high_risk) is False


def test_detect_cannibalization():
    entries = [
        {"keyword": "a", "mappedPageId": "page1", "parentTopic": "topic1"},
        {"keyword": "b", "mappedPageId": "page1", "parentTopic": "topic1"},
        {"keyword": "c", "mappedPageId": "page2", "parentTopic": "topic2"},
    ]
    flagged = competitor_and_gap.detect_cannibalization(entries)
    assert flagged == {"a", "b"}


def test_compute_confidence_from_subscores_renormalizes():
    all_four = confidence.compute_confidence_from_subscores({"gsc": 80, "ga4": 60, "ads": 40, "semrush": 90})
    assert 0 <= all_four <= 100

    semrush_only = confidence.compute_confidence_from_subscores(
        {"gsc": None, "ga4": None, "ads": None, "semrush": 90}
    )
    assert semrush_only == 90  # only source present -> its own score, fully renormalized


def test_build_entry_matches_page_quality_dashboard():
    page_titles = {"panchakarma-treatment": "Panchakarma Treatment"}
    semrush_data = {"volumeByCountry": {"in": 2900, "us": 320}, "cpc": 145, "difficulty": 38, "parentTopic": "panchakarma treatment"}
    gsc_entry = {"impressions": 4800, "clicks": 310, "ctr": 6.5, "position": 4.2, "page": "panchakarma-treatment"}
    entry = entry_builder.build_entry(
        "panchakarma treatment kerala", semrush_data, gsc_entry, None, None, None, set(), page_titles, HV
    )
    assert entry["mappedPage"] == "Panchakarma Treatment"
    assert entry["type"] == "Primary"
    assert entry["suggestedPlacement"] == "H1"
    assert "priority" in entry and entry["priority"] in ("High", "Medium", "Low")


def test_build_entry_for_villaraag_uses_its_own_context():
    page_titles = {}
    semrush_data = {"volumeByCountry": {"in": 2900}, "cpc": 145, "difficulty": 38, "parentTopic": None}
    entry = entry_builder.build_entry(
        "private pool villa goa", semrush_data, None, None, None, None, set(), page_titles, VR
    )
    assert entry["spamRisk"] == "None"
    assert entry["complianceRisk"] == "Low"


def test_priority_band_low_for_spam_or_high_compliance_risk():
    base = {"spamRisk": "None", "intent": "Commercial", "complianceRisk": "Low",
            "audienceFitScore": "High", "confidenceScore": 90}
    assert entry_builder.priority_band(base) == "High"

    spam = dict(base, spamRisk="Flagged")
    assert entry_builder.priority_band(spam) == "Low"

    risky = dict(base, complianceRisk="High")
    assert entry_builder.priority_band(risky) == "Low"

    low_confidence = dict(base, confidenceScore=20)
    assert entry_builder.priority_band(low_confidence) == "Medium"


def test_enrich_with_cached_signal_borrows_gsc_ga4_ads():
    page_titles = {}
    semrush_only = entry_builder.build_entry(
        "panchakarma treatment kerala",
        {"volumeByCountry": {"in": 2900}, "cpc": 145, "difficulty": 38, "parentTopic": "panchakarma treatment"},
        None, None, None, None, set(), page_titles, HV,
    )
    assert semrush_only["crossSourceConfidence"]["subscores"]["gsc"] is None

    cached_entry = {
        "mappedPageId": "panchakarma-treatment",
        "mappedPage": "Panchakarma Treatment",
        "coreSearchMetrics": {"currentRankingPosition": 4.2},
        "underperformanceFlag": False,
        "crossSourceConfidence": {"subscores": {"gsc": 96, "ga4": 85, "ads": 70, "semrush": 60}},
    }
    original_semrush_only_score = semrush_only["confidenceScore"]
    enriched = entry_builder.enrich_with_cached_signal(semrush_only, cached_entry)
    assert enriched["mappedPage"] == "Panchakarma Treatment"
    assert enriched["coreSearchMetrics"]["currentRankingPosition"] == 4.2
    assert enriched["crossSourceConfidence"]["subscores"]["gsc"] == 96
    assert 0 <= enriched["confidenceScore"] <= 100
    # composite confidence now blends GSC/GA4/Ads too, not Semrush alone -> should shift
    assert enriched["confidenceScore"] != original_semrush_only_score

def test_enrich_with_cached_signal_recomputes_placement():
    page_titles = {}
    semrush_only = entry_builder.build_entry(
        "panchakarma treatment kerala",
        {"volumeByCountry": {"in": 2900}, "cpc": 145, "difficulty": 38, "parentTopic": "panchakarma treatment"},
        None, None, None, None, set(), page_titles, HV,
    )
    assert semrush_only["type"] == "Primary"
    assert semrush_only["suggestedPlacement"] == "Meta Title"  # no mapped page yet

    cached_entry = {
        "mappedPageId": "panchakarma-treatment",
        "mappedPage": "Panchakarma Treatment",
        "coreSearchMetrics": {"currentRankingPosition": 4.2},
        "underperformanceFlag": False,
        "crossSourceConfidence": {"subscores": {"gsc": 96, "ga4": 85, "ads": 70, "semrush": 60}},
    }
    enriched = entry_builder.enrich_with_cached_signal(semrush_only, cached_entry)
    assert enriched["suggestedPlacement"] == "H1"  # now that a page is mapped


def test_enrich_with_cached_signal_no_match_leaves_entry_unchanged():
    page_titles = {}
    fresh_entry = entry_builder.build_entry(
        "panchakarma treatment kerala",
        {"volumeByCountry": {"in": 2900}, "cpc": 145, "difficulty": 38, "parentTopic": "panchakarma treatment"},
        None, None, None, None, set(), page_titles, HV,
    )
    no_match = entry_builder.enrich_with_cached_signal(fresh_entry, None)
    assert no_match["crossSourceConfidence"]["subscores"]["gsc"] is None


def test_extract_seed_phrases_finds_repeated_phrase():
    text = (
        "panchakarma treatment kerala is popular. Our panchakarma treatment kerala "
        "program includes panchakarma treatment kerala for chronic pain."
    )
    phrases = phrase_extraction.extract_seed_phrases(text, limit=3)
    assert any("panchakarma treatment" in p for p in phrases)


def test_extract_seed_phrases_empty_text():
    assert phrase_extraction.extract_seed_phrases("") == []
    assert phrase_extraction.extract_seed_phrases("   ") == []


def test_content_words_filters_stopwords():
    words = phrase_extraction.content_words("The Best Ayurveda Hospital in Kerala")
    assert "best" in words and "ayurveda" in words and "hospital" in words and "kerala" in words
    assert "the" not in words and "in" not in words


def test_ai_keyword_ideation_normalize_dedupes_and_lowercases():
    normalized = ai_keyword_ideation.normalize_keywords(
        ["Panchakarma Treatment Kerala", "panchakarma treatment kerala", "What is Panchakarma?"]
    )
    assert normalized == ["panchakarma treatment kerala", "what is panchakarma?"]


def test_ai_keyword_ideation_normalize_caps_at_max():
    many = [f"keyword {i}" for i in range(40)]
    assert len(ai_keyword_ideation.normalize_keywords(many)) == ai_keyword_ideation.MAX_KEYWORDS


def test_ai_keyword_ideation_build_input_text():
    text = ai_keyword_ideation.build_input_text("panchakarma", "some page content")
    assert "panchakarma" in text
    assert "some page content" in text
    assert ai_keyword_ideation.build_input_text("", "") == ""


def test_ai_keyword_ideation_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    try:
        ai_keyword_ideation.suggest_keywords("panchakarma", HV)
        assert False, "should have raised RuntimeError"
    except RuntimeError as e:
        assert "ANTHROPIC_API_KEY" in str(e)


def test_is_patient_nationality_pattern_flags_specific_country():
    assert compliance.is_patient_nationality_pattern("ayurveda treatment kerala for uk patients", HV) is True
    assert compliance.is_patient_nationality_pattern("ayurveda hospital kerala for german patients", HV) is True
    assert compliance.is_patient_nationality_pattern("ayurveda retreat dubai patients kerala", HV) is True


def test_is_patient_nationality_pattern_allows_generic_terms():
    # "international"/"foreigners"/"nri" are legitimate existing keywords
    # elsewhere in this dataset -- must NOT be caught by this rule.
    assert compliance.is_patient_nationality_pattern("ayurvedic wellness retreat for international patients", HV) is False
    assert compliance.is_patient_nationality_pattern("ayurveda treatment for foreigners kerala", HV) is False
    assert compliance.is_patient_nationality_pattern("ayurvedic hospital for nri", HV) is False
    assert compliance.is_patient_nationality_pattern("panchakarma treatment kerala", HV) is False


def test_is_patient_nationality_pattern_not_applicable_for_villaraag():
    # Villaraag has no nationality_country_terms configured -- always False.
    assert compliance.is_patient_nationality_pattern("villa for uk patients", VR) is False


def test_compliance_check_marks_patient_nationality_pattern_high():
    result = compliance.compliance_check("ayurveda treatment kerala for uk patients", HV)
    assert result["overallRisk"] == "High"
    assert result["patientNationalityPattern"] is True


def test_find_restricted_seed_terms_matches_policy_phrases():
    assert compliance.find_restricted_seed_terms("ayurveda resort kerala", HV) == ["resort"]
    assert compliance.find_restricted_seed_terms("permanent cure for back pain", HV) == ["permanent cure"]
    assert set(compliance.find_restricted_seed_terms("guest spa treatment", HV)) == {"guest", "spa"}


def test_find_restricted_seed_terms_word_boundary_avoids_false_positive():
    # "spa" must not match inside "spasm" -- word-boundary regex, not substring
    assert compliance.find_restricted_seed_terms("muscle spasm treatment kerala", HV) == []
    assert compliance.find_restricted_seed_terms("ayurvedic panchakarma treatment", HV) == []


def test_find_restricted_seed_terms_matches_simple_plural():
    # Regression: found live -- "ayurveda retreat for international guests"
    # (plural) slipped past the filter because the source policy doc only
    # lists "Guest" (singular) and the matcher was an exact word-boundary
    # match with no plural handling.
    assert compliance.find_restricted_seed_terms("ayurveda retreat for international guests", HV) == ["guest"]
    assert compliance.find_restricted_seed_terms("ayurveda resorts in kerala", HV) == ["resort"]
    assert compliance.find_restricted_seed_terms("cancer treatments available", HV) == ["cancer treatment"]


def test_find_restricted_seed_terms_empty_for_clean_keyword():
    assert compliance.find_restricted_seed_terms("panchakarma treatment kerala", HV) == []
    assert compliance.find_restricted_seed_terms("", HV) == []


def test_find_restricted_seed_terms_villaraag_uses_its_own_list():
    # Villaraag's restricted list is explicit/adult-content only -- "resort"
    # and "spa" are fine here (opposite of Healing Village).
    assert compliance.find_restricted_seed_terms("luxury resort spa goa", VR) == []
    assert compliance.find_restricted_seed_terms("escort service goa", VR) == ["escort"]


def test_resolve_ga4_entry_sample_phase_keyed_by_keyword():
    ga4_data = {"panchakarma treatment kerala": {"sessions": 100}}
    result = entry_builder.resolve_ga4_entry("sample", "panchakarma treatment kerala", {"page": "panchakarma-treatment"}, ga4_data)
    assert result == {"sessions": 100}


def test_resolve_ga4_entry_live_phase_keyed_by_page():
    ga4_data = {"panchakarma-treatment": {"sessions": 250}}
    gsc_entry = {"page": "panchakarma-treatment"}
    result = entry_builder.resolve_ga4_entry("live", "panchakarma treatment kerala", gsc_entry, ga4_data)
    assert result == {"sessions": 250}

    # unmapped keyword (no GSC page) -> no GA4 signal, live phase
    assert entry_builder.resolve_ga4_entry("live", "some new keyword", None, ga4_data) is None
