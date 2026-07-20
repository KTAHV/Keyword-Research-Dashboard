"""
Schema sanity check for data/keyword_research_data.json -- no browser
needed. Run after build_keyword_research_dashboard.py.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_JSON = os.path.join(ROOT, "data", "keyword_research_data.json")

REQUIRED_TOP_KEYS = [
    "generatedAt", "phase", "kpis", "kpiDeltas", "entries", "needsAttention",
    "topContentGapOpportunities", "avoidList", "competitorGapList", "underperformingPages",
]
REQUIRED_ENTRY_KEYS = [
    "keyword", "type", "suggestedPlacement", "answerable", "intent", "aiVoiceSearchFit",
    "audienceFitScore", "spamRisk", "complianceRisk", "confidenceScore", "mappedPage",
    "coreSearchMetrics", "audienceFitIntent", "aiVoiceReadiness", "complianceCheck",
    "crossSourceConfidence",
]
VALID_TYPE = {"Primary", "Secondary", "Long-tail", "Question"}
VALID_INTENT = {"Commercial", "Informational", "Navigational", "Low-Quality"}
VALID_BAND = {"High", "Medium", "Low"}
VALID_SPAM = {"None", "Flagged"}


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def main():
    if not os.path.exists(DATA_JSON):
        fail(f"{DATA_JSON} does not exist -- run build_keyword_research_dashboard.py first.")

    with open(DATA_JSON, encoding="utf-8") as f:
        data = json.load(f)

    for key in REQUIRED_TOP_KEYS:
        if key not in data:
            fail(f"missing top-level key '{key}'")

    if not data["entries"]:
        fail("entries is empty")

    for e in data["entries"]:
        for key in REQUIRED_ENTRY_KEYS:
            if key not in e:
                fail(f"entry '{e.get('keyword', '?')}' missing key '{key}'")
        if e["type"] not in VALID_TYPE:
            fail(f"entry '{e['keyword']}' has invalid type '{e['type']}'")
        if e["intent"] not in VALID_INTENT:
            fail(f"entry '{e['keyword']}' has invalid intent '{e['intent']}'")
        if e["audienceFitScore"] not in VALID_BAND:
            fail(f"entry '{e['keyword']}' has invalid audienceFitScore '{e['audienceFitScore']}'")
        if e["spamRisk"] not in VALID_SPAM:
            fail(f"entry '{e['keyword']}' has invalid spamRisk '{e['spamRisk']}'")
        if not (0 <= e["confidenceScore"] <= 100):
            fail(f"entry '{e['keyword']}' has out-of-range confidenceScore {e['confidenceScore']}")

    print(f"OK: {len(data['entries'])} keyword entries, phase={data['phase']}")


if __name__ == "__main__":
    main()
