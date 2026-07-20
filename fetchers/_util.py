import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_DIR = os.path.join(ROOT, "data", "sample")


def load_sample(filename):
    path = os.path.join(SAMPLE_DIR, filename)
    with open(path, encoding="utf-8") as f:
        return json.load(f)
