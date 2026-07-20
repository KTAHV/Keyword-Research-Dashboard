"""
Compliance Check: Medical/Health Compliance Risk, Google Ads Healthcare &
Medicines Policy risk, and Search Engine/YMYL Policy risk. Term-matching
against config.COMPLIANCE_RISK_TERMS (cure/guarantee/miracle-type language)
-- the same phrasing that both Google Ads' healthcare policy and general
YMYL guidance flag as unsubstantiated medical claims.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402


def _matched_risk_terms(keyword):
    kw = keyword.lower()
    return [t for t in config.COMPLIANCE_RISK_TERMS if t in kw]


def compliance_check(keyword):
    matches = _matched_risk_terms(keyword)
    if not matches:
        return {
            "medicalComplianceRisk": "Low",
            "adsHealthcarePolicyRisk": "Low",
            "ymylPolicyRisk": "Low",
            "overallRisk": "Low",
            "flaggedTerms": [],
        }

    severity = "High" if len(matches) > 1 or any(t in ("cure", "guaranteed", "miracle") for t in matches) else "Medium"
    return {
        "medicalComplianceRisk": severity,
        "adsHealthcarePolicyRisk": severity,
        "ymylPolicyRisk": severity,
        "overallRisk": severity,
        "flaggedTerms": matches,
    }
