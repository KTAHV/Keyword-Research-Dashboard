"""
AI & Voice Search Readiness: AEO Score, Answerability Score, GEO/GAI
Visibility Potential, and Structured-Data/Schema Readiness.

These are keyword-level heuristics (question shape, specificity, word
count) that estimate how *answerable* a keyword is in a snippet/voice/AI-
chat context -- not a guarantee, since actual AEO/GEO performance also
depends on the page content, which is out of scope for a keyword-research
pass.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402
from analysis.intent_and_audience import is_question  # noqa: E402


def aeo_score(keyword):
    score = 20
    if is_question(keyword):
        score += 45
    word_count = len(keyword.split())
    if 4 <= word_count <= 9:
        score += 20
    elif word_count > 9:
        score += 5
    first_word = keyword.strip().lower().split(" ", 1)[0]
    if first_word in ("what", "how", "why"):
        score += 15
    return min(100, score)


def answerability_score(keyword):
    """Higher when the keyword is specific enough to answer in ~40-60 words."""
    word_count = len(keyword.split())
    score = 30
    if is_question(keyword):
        score += 30
    if 3 <= word_count <= 8:
        score += 30
    elif word_count > 12:
        score -= 10
    return max(0, min(100, score))


def geo_visibility_score(keyword, medical_specificity_score_value):
    """E-E-A-T-rich content fit -- rewards specific, informational,
    medically-grounded queries (the kind AI answer engines prefer to cite
    an accredited-hospital source for)."""
    score = 25
    if is_question(keyword):
        score += 20
    score += min(medical_specificity_score_value, 100) * 0.35
    return max(0, min(100, round(score)))


def schema_readiness(keyword):
    kw = keyword.strip().lower()
    if kw.startswith("how to"):
        return "HowTo Schema"
    if is_question(keyword):
        return "FAQ Schema"
    return "None"


def ai_voice_fit(keyword, medical_specificity_score_value):
    aeo = aeo_score(keyword)
    answerability = answerability_score(keyword)
    geo = geo_visibility_score(keyword, medical_specificity_score_value)
    weights = config.AI_VOICE_WEIGHTS
    composite = round(
        weights["aeoScore"] * aeo
        + weights["answerabilityScore"] * answerability
        + weights["geoVisibilityScore"] * geo
    )
    label = config.band_for_score(composite, bands=[("High", 65), ("Medium", 40), ("Low", 0)])
    return {
        "aeoScore": aeo,
        "answerabilityScore": answerability,
        "geoVisibilityScore": geo,
        "schemaReadiness": schema_readiness(keyword),
        "compositeScore": composite,
        "fit": label,
    }
