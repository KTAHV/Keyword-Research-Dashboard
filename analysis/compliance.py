"""
Compliance Check: Medical/Health Compliance Risk, Google Ads Healthcare &
Medicines Policy risk, and Search Engine/YMYL Policy risk. Two independent
triggers, both High-risk:
1. config.COMPLIANCE_RISK_TERMS (cure/guarantee/miracle-type language) --
   the same phrasing that both Google Ads' healthcare policy and general
   YMYL guidance flag as unsubstantiated medical claims.
2. "patient(s)" paired with a specific nationality/country name (e.g. "...
   for uk patients") -- reads as a targeted medical claim about that
   population. See is_patient_nationality_pattern().
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402

_PATIENT_RE = re.compile(r"\bpatients?\b", re.IGNORECASE)
_NATIONALITY_RES = [re.compile(rf"\b{re.escape(t)}\b", re.IGNORECASE) for t in config.NATIONALITY_COUNTRY_TERMS]
_RESTRICTED_SEED_RES = [
    (term, re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE))
    for term in config.RESTRICTED_SEED_TERMS_AHV
]


def find_restricted_seed_terms(text):
    """Returns every config.RESTRICTED_SEED_TERMS_AHV phrase found in `text`
    (case-insensitive, word-boundary matched so short entries like "spa"
    don't false-positive inside unrelated words like "spasm"). Used by the
    live Search tool to block a search on the typed seed outright -- see
    api/search.py's module docstring -- and to drop any AI-suggested/
    discovered keyword that still contains one of these terms."""
    if not text:
        return []
    return [term for term, pattern in _RESTRICTED_SEED_RES if pattern.search(text)]


def _matched_risk_terms(keyword):
    kw = keyword.lower()
    return [t for t in config.COMPLIANCE_RISK_TERMS if t in kw]


def is_patient_nationality_pattern(keyword):
    """True if `keyword` pairs "patient(s)" with a specific nationality/
    country name -- e.g. "ayurveda treatment package for uk patients".
    Generic terms ("international", "foreigners", "nri") do NOT trigger
    this -- only naming a specific country/nationality does."""
    if not _PATIENT_RE.search(keyword):
        return False
    return any(pattern.search(keyword) for pattern in _NATIONALITY_RES)


def compliance_check(keyword):
    matches = _matched_risk_terms(keyword)
    nationality_pattern = is_patient_nationality_pattern(keyword)

    if not matches and not nationality_pattern:
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
