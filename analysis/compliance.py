"""
Compliance Check. Per brand (config.BrandConfig):
- If `brand.medical_compliance_enabled`: Medical/Health Compliance Risk,
  Google Ads Healthcare & Medicines Policy risk, and Search Engine/YMYL
  Policy risk, exactly as before -- two independent High-risk triggers,
  `brand.compliance_risk_terms` (cure/guarantee/miracle-type language) and
  "patient(s)" paired with a specific nationality/country name (see
  is_patient_nationality_pattern()).
- If not (e.g. Villaraag, a leisure resort with no medical-claims
  category): the Compliance column instead reflects only
  `brand.restricted_seed_terms` matches (explicit/adult-content terms for
  Villaraag) -- same column, narrower brand-appropriate logic.

`find_restricted_seed_terms()` is brand-independent of the above: it's
used by the live Search tool to hard-block a typed seed outright (see
api/search.py's module docstring) for *every* brand, not just non-medical
ones -- Healing Village's own restricted policy (Google Ads weight-loss +
tax-compliance + medical-claims doc) still blocks searches the same way
it always has.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402

_PATIENT_RE = re.compile(r"\bpatients?\b", re.IGNORECASE)

# Compiled once per brand on first use, keyed by brand.key -- avoids
# recompiling ~150 regexes on every single keyword check.
_nationality_res_cache = {}
_restricted_seed_res_cache = {}


def _nationality_res(brand):
    cached = _nationality_res_cache.get(brand.key)
    if cached is None:
        cached = [re.compile(rf"\b{re.escape(t)}\b", re.IGNORECASE) for t in brand.nationality_country_terms]
        _nationality_res_cache[brand.key] = cached
    return cached


def _restricted_seed_res(brand):
    cached = _restricted_seed_res_cache.get(brand.key)
    if cached is None:
        # Trailing "s?" so a simple plural of the term's last word
        # ("guests", "resorts", "cancer treatments") still matches --
        # confirmed live that AI-suggested phrasing routinely pluralizes
        # these, and source policy docs only list singular forms.
        cached = [(term, re.compile(rf"\b{re.escape(term)}s?\b", re.IGNORECASE)) for term in brand.restricted_seed_terms]
        _restricted_seed_res_cache[brand.key] = cached
    return cached


def find_restricted_seed_terms(text, brand):
    """Returns every brand.restricted_seed_terms phrase found in `text`
    (case-insensitive, word-boundary matched so short entries like "spa"
    don't false-positive inside unrelated words like "spasm"; a trailing
    simple plural of the term also matches). Used by the live Search tool
    to block a search on the typed seed outright, and to drop any AI-
    suggested/discovered keyword that still contains one of these terms."""
    if not text:
        return []
    return [term for term, pattern in _restricted_seed_res(brand) if pattern.search(text)]


def _matched_risk_terms(keyword, brand):
    kw = keyword.lower()
    return [t for t in brand.compliance_risk_terms if t in kw]


def is_patient_nationality_pattern(keyword, brand):
    """True if `keyword` pairs "patient(s)" with a specific nationality/
    country name -- e.g. "ayurveda treatment package for uk patients".
    Generic terms ("international", "foreigners", "nri") do NOT trigger
    this -- only naming a specific country/nationality does. Always False
    for brands with no nationality_country_terms (e.g. Villaraag)."""
    if not brand.nationality_country_terms:
        return False
    if not _PATIENT_RE.search(keyword):
        return False
    return any(pattern.search(keyword) for pattern in _nationality_res(brand))


def compliance_check(keyword, brand):
    if brand.medical_compliance_enabled:
        matches = _matched_risk_terms(keyword, brand)
        nationality_pattern = is_patient_nationality_pattern(keyword, brand)
        restricted_matches = []
    else:
        matches = []
        nationality_pattern = False
        restricted_matches = find_restricted_seed_terms(keyword, brand)

    if not matches and not nationality_pattern and not restricted_matches:
        return {
            "medicalComplianceRisk": "Low",
            "adsHealthcarePolicyRisk": "Low",
            "ymylPolicyRisk": "Low",
            "overallRisk": "Low",
            "flaggedTerms": [],
            "patientNationalityPattern": False,
        }

    if nationality_pattern:
        severity = "High"
        flagged = matches + ["patient + specific nationality/country"]
    elif restricted_matches:
        severity = "High"
        flagged = restricted_matches
    else:
        severity = "High" if len(matches) > 1 or any(t in ("cure", "guaranteed", "miracle") for t in matches) else "Medium"
        flagged = matches

    return {
        "medicalComplianceRisk": severity,
        "adsHealthcarePolicyRisk": severity,
        "ymylPolicyRisk": severity,
        "overallRisk": severity,
        "flaggedTerms": flagged,
        "patientNationalityPattern": nationality_pattern,
    }
