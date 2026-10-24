"""Shared helpers: load the golden set, run the agent over it, pretty printing."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
RESULTS = os.path.join(ROOT, "results")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent import run_agent  # noqa: E402


def load_golden(path=None):
    path = path or os.path.join(DATA, "golden.jsonl")
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def run_suite(version="v1", cases=None):
    """Run the agent on every golden case; return list of (case, trace_dict)."""
    cases = cases or load_golden()
    return [(c, run_agent(c["input"], version).to_dict()) for c in cases]


def get_version(default="v1"):
    for a in sys.argv[1:]:
        if a.startswith("v"):
            return a
    return default


def header(title):
    print("\n" + "=" * 72 + f"\n  {title}\n" + "=" * 72)


def mark(ok):
    return "PASS" if ok else "FAIL"


def save_json(name, obj):
    os.makedirs(RESULTS, exist_ok=True)
    path = os.path.join(RESULTS, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    return path
