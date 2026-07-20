"""
Audience Fit & Intent: intent classification, spam/low-quality exclusion,
Audience-Fit Score, and Medical/Therapeutic Specificity Score. All matching
is substring-based against the vocabulary lists in config.py -- deliberately
simple and auditable (a marketer can read config.py and know exactly why a
keyword landed where it did) rather than a black-box classifier.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402


def _contains_any(keyword, terms):
    kw = keyword.lower()
    return [t for t in terms if t in kw]


def spam_risk_flag(keyword):
    return "Flagged" if _contains_any(keyword, config.SPAM_TERMS) else "None"


def is_question(keyword):
    first_word = keyword.strip().lower().split(" ", 1)[0]
    return first_word in config.QUESTION_STARTERS


def classify_intent(keyword):
    """Commercial / Informational / Navigational / Low-Quality."""
    if _contains_any(keyword, config.SPAM_TERMS):
        return "Low-Quality"
    if _contains_any(keyword, config.DIY_HOME_REMEDY_TERMS):
        return "Low-Quality"
    if _contains_any(keyword, config.JOB_SEEKER_TERMS):
        return "Low-Quality"

    kw = keyword.lower()
    competitor_names = [c["name"].lower().split(" ")[0] for c in config.TIER_A_COMPETITORS]
    if any(name in kw for name in competitor_names) or " vs " in kw:
        return "Navigational"

    if is_question(keyword):
        return "Informational"

    commercial_signals = ["treatment", "package", "packages", "hospital", "retreat", "resort", "cost", "for "]
    if _contains_any(keyword, commercial_signals):
        return "Commercial"

    return "Informational"


def medical_specificity_score(keyword):
    matches = _contains_any(keyword, config.MEDICAL_SPECIFICITY_TERMS)
    return min(100, len(matches) * 35 + (20 if matches else 0))


def audience_fit_raw_score(keyword, volume_by_country, cpc):
    """0-100 raw score, banded to High/Medium/Low by caller."""
    if _contains_any(keyword, config.SPAM_TERMS):
        return 0
    if _contains_any(keyword, config.DIY_HOME_REMEDY_TERMS + config.JOB_SEEKER_TERMS):
        return 15

    score = 40
    score += min(len(_contains_any(keyword, config.MEDICAL_SPECIFICITY_TERMS)), 3) * 12
    score += min(len(_contains_any(keyword, config.QUALITY_CONSCIOUS_TERMS)), 2) * 10
    # Higher CPC is a proxy for a spend-capable, commercially serious audience
    # -- deliberately not tied to any specific price figure.
    if cpc and cpc >= 150:
        score += 15
    elif cpc and cpc >= 100:
        score += 8
    # International (higher-propensity-to-pay) volume nudges fit upward.
    intl_volume = sum(v for c, v in (volume_by_country or {}).items() if c != "in")
    if intl_volume >= 300:
        score += 10
    return min(100, score)


def audience_fit_score(keyword, volume_by_country, cpc):
    raw = audience_fit_raw_score(keyword, volume_by_country, cpc)
    return config.band_for_score(raw, bands=[("High", 70), ("Medium", 40), ("Low", 0)])
