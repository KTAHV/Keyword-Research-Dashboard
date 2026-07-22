"""
Schema sanity check for data/keyword_research_data_<brand>.json -- no
browser needed. Run after build_keyword_research_dashboard.py. Checks
every brand data file found on disk unless --brand narrows it to one.
"""
import argparse
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")

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


def verify_one(data_json_path):
    if not os.path.exists(data_json_path):
        fail(f"{data_json_path} does not exist -- run build_keyword_research_dashboard.py first.")

    with open(data_json_path, encoding="utf-8") as f:
        data = json.load(f)

    for key in REQUIRED_TOP_KEYS:
        if key not in data:
            fail(f"{data_json_path}: missing top-level key '{key}'")

    if not data["entries"]:
        fail(f"{data_json_path}: entries is empty")

    for e in data["entries"]:
        for key in REQUIRED_ENTRY_KEYS:
            if key not in e:
                fail(f"{data_json_path}: entry '{e.get('keyword', '?')}' missing key '{key}'")
        if e["type"] not in VALID_TYPE:
            fail(f"{data_json_path}: entry '{e['keyword']}' has invalid type '{e['type']}'")
        if e["intent"] not in VALID_INTENT:
            fail(f"{data_json_path}: entry '{e['keyword']}' has invalid intent '{e['intent']}'")
        if e["audienceFitScore"] not in VALID_BAND:
            fail(f"{data_json_path}: entry '{e['keyword']}' has invalid audienceFitScore '{e['audienceFitScore']}'")
        if e["spamRisk"] not in VALID_SPAM:
            fail(f"{data_json_path}: entry '{e['keyword']}' has invalid spamRisk '{e['spamRisk']}'")
        if not (0 <= e["confidenceScore"] <= 100):
            fail(f"{data_json_path}: entry '{e['keyword']}' has out-of-range confidenceScore {e['confidenceScore']}")

    print(f"OK: {os.path.basename(data_json_path)}: {len(data['entries'])} keyword entries, phase={data['phase']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--brand", default=None, help="Check only data/keyword_research_data_<brand>.json")
    args = parser.parse_args()

    if args.brand:
        verify_one(os.path.join(DATA_DIR, f"keyword_research_data_{args.brand}.json"))
        return

    paths = sorted(glob.glob(os.path.join(DATA_DIR, "keyword_research_data_*.json")))
    if not paths:
        fail(f"no keyword_research_data_*.json files found in {DATA_DIR} -- run build_keyword_research_dashboard.py first.")
    for path in paths:
        verify_one(path)


if __name__ == "__main__":
    main()
