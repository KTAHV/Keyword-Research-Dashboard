"""
Cross-Source Confidence: combines GSC + GA4 + Google Ads + Semrush signals
(whichever are present for a given keyword) into one 0-100 Confidence Score,
and flags "Underperformance" -- a keyword that ranks well in GSC but shows
poor GA4 engagement, meaning the ranking is fine but the page content isn't
converting the visit (a content problem, not a visibility problem).

Renormalizes config.CONFIDENCE_WEIGHTS over whichever sources actually have
data for a keyword, same pattern as Page Quality Dashboard's tier2 weight
renormalization for non-English pages.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402


def _clamp(v, lo=0, hi=100):
    return max(lo, min(hi, v))


def _gsc_subscore(gsc):
    if not gsc:
        return None
    position = gsc.get("position", 100)
    position_points = 40 if position <= 10 else 20 if position <= 20 else 5
    ctr_points = min(gsc.get("ctr", 0) * 4, 30)
    impressions_points = min(gsc.get("impressions", 0) / 100, 30)
    return _clamp(round(position_points + ctr_points + impressions_points))


def _ga4_subscore(ga4):
    if not ga4:
        return None
    engagement_points = min(ga4.get("engagementRate", 0), 100) * 0.6
    conversion_points = min(ga4.get("conversions", 0) * 6, 40)
    return _clamp(round(engagement_points + conversion_points))


def _ads_subscore(ads):
    if not ads:
        return None
    conversion_points = min(ads.get("conversions", 0) * 8, 60)
    click_points = min(ads.get("clicks", 0) / 5, 40)
    return _clamp(round(conversion_points + click_points))


def _semrush_subscore(volume_by_country, difficulty):
    total_volume = sum((volume_by_country or {}).values())
    volume_points = min(total_volume / 50, 70)
    difficulty_points = (100 - (difficulty or 50)) * 0.3
    return _clamp(round(volume_points + difficulty_points))


def compute_confidence_from_subscores(subscores):
    """subscores: dict with any subset of gsc/ga4/ads/semrush keys, values
    0-100 or None. Renormalizes config.CONFIDENCE_WEIGHTS over whichever
    keys are present and not None. Returns the composite 0-100 score."""
    available = {k: v for k, v in subscores.items() if v is not None}
    weights = {k: config.CONFIDENCE_WEIGHTS[k] for k in available}
    weight_sum = sum(weights.values()) or 1
    return round(sum(available[k] * (weights[k] / weight_sum) for k in available))


def compute_confidence(gsc, ga4, ads, volume_by_country, difficulty):
    subscores = {
        "gsc": _gsc_subscore(gsc),
        "ga4": _ga4_subscore(ga4),
        "ads": _ads_subscore(ads),
        "semrush": _semrush_subscore(volume_by_country, difficulty),
    }
    composite = compute_confidence_from_subscores(subscores)
    return composite, subscores


def underperformance_flag(gsc, ga4):
    if not gsc or not ga4:
        return False
    good_rank = gsc.get("position", 100) <= 10
    poor_engagement = ga4.get("engagementRate", 100) < 30
    return good_rank and poor_engagement
