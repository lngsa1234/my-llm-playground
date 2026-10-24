"""
STEP 1 — GOLDEN DATASETS
A golden dataset is a small, hand-curated set of inputs with the *expected*
behavior written down. Every later step grades against it, so its quality
caps the quality of all your evals.

This script lints the dataset: schema, duplicates, coverage, and blind spots.
Run:  python lab/step1_golden.py
"""
from collections import Counter

from common import header, load_golden

REQUIRED = ["id", "category", "difficulty", "input", "expected"]
EXPECTED_KEYS = ["must_contain", "must_not_contain", "expected_tools",
                 "expected_args", "forbidden_tools", "expected_state"]


def lint(cases):
    problems, warnings = [], []
    ids = Counter(c.get("id") for c in cases)
    for dup, n in ids.items():
        if n > 1:
            problems.append(f"duplicate id '{dup}' appears {n}x")
    for c in cases:
        cid = c.get("id", "?")
        for k in REQUIRED:
            if k not in c:
                problems.append(f"{cid}: missing field '{k}'")
        exp = c.get("expected", {})
        for k in EXPECTED_KEYS:
            if k not in exp:
                problems.append(f"{cid}: expected.{k} missing")
        if not exp.get("must_contain") and not exp.get("must_not_contain"):
            warnings.append(f"{cid}: no answer checks -- how will you know it passed?")
        if not exp.get("must_not_contain") and not exp.get("forbidden_tools"):
            warnings.append(f"{cid}: no negative checks (what must NOT happen?)")
        if not c.get("notes"):
            warnings.append(f"{cid}: no notes -- future-you won't know why this case exists")
    return problems, warnings


def coverage(cases):
    cats = Counter(c["category"] for c in cases)
    diff = Counter(c["difficulty"] for c in cases)
    side_effect = sum(1 for c in cases if any(
        t in c["expected"]["expected_tools"] or t in c["expected"]["forbidden_tools"]
        for t in ("send_email", "create_event")))
    return cats, diff, side_effect


if __name__ == "__main__":
    cases = load_golden()
    header(f"STEP 1: Golden dataset — {len(cases)} cases")

    problems, warnings = lint(cases)
    print("\nSchema problems:", "none ✓" if not problems else "")
    for p in problems:
        print("  ✗", p)
    print("\nQuality warnings:", "none ✓" if not warnings else "")
    for w in warnings:
        print("  !", w)

    cats, diff, side = coverage(cases)
    print("\nCoverage by category:")
    for k, v in sorted(cats.items()):
        flag = "   <- thin, add more" if v < 2 else ""
        print(f"  {k:<15} {'█' * v} {v}{flag}")
    print("\nBy difficulty:", dict(diff))
    print(f"Cases touching side-effecting tools (email/booking): {side}")

    hard_share = diff.get("hard", 0) / len(cases)
    print(f"\nHard-case share: {hard_share:.0%}"
          + ("  (aim for 25%+: hard cases are where agents break)" if hard_share < 0.25 else " ✓"))
    print("\nTip: every bug you find in production should become a new golden case.")
