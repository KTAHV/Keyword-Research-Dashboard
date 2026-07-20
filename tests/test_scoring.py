import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis import ai_voice_readiness, competitor_and_gap, compliance, confidence, intent_and_audience


def test_spam_risk_flag():
    assert intent_and_audience.spam_risk_flag("ayurvedic massage near me") == "Flagged"
    assert intent_and_audience.spam_risk_flag("panchakarma treatment kerala") == "None"


def test_classify_intent_low_quality():
    assert intent_and_audience.classify_intent("ayurvedic massage near me") == "Low-Quality"
    assert intent_and_audience.classify_intent("ayurveda home remedies for weight loss") == "Low-Quality"
    assert intent_and_audience.classify_intent("ayurveda hospital jobs kerala") == "Low-Quality"


def test_classify_intent_informational_question():
    assert intent_and_audience.classify_intent("what is panchakarma treatment") == "Informational"


def test_classify_intent_commercial():
    assert intent_and_audience.classify_intent("panchakarma treatment kerala") == "Commercial"


def test_audience_fit_score_bands():
    high = intent_and_audience.audience_fit_score(
        "best ayurveda hospital kerala", {"in": 3600, "us": 410, "uk": 260, "ae": 520}, 158
    )
    assert high == "High"
    spam = intent_and_audience.audience_fit_score("ayurvedic massage near me", {"in": 8100}, 39)
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
    result = compliance.compliance_check("guaranteed cure for chronic pain ayurveda")
    assert result["overallRisk"] == "High"
    assert "cure" in result["flaggedTerms"]

    clean = compliance.compliance_check("panchakarma treatment kerala")
    assert clean["overallRisk"] == "Low"
    assert clean["flaggedTerms"] == []


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
