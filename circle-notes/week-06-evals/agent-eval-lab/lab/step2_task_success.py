"""
STEP 2 — TASK SUCCESS (outcome evaluation)
Question: did the agent actually get the job done?
We only look at the OUTCOME -- the final answer and the end state of the
world (events booked, emails sent). How it got there is Step 3's job.

Run:  python lab/step2_task_success.py        (baseline agent)
      python lab/step2_task_success.py v2     (the "new" agent)
"""
from collections import defaultdict

from common import get_version, header, mark, run_suite


def evaluate_task(case, trace):
    exp = case["expected"]
    ans = trace["answer"].lower()
    checks = {}
    for s in exp["must_contain"]:
        checks[f"contains '{s}'"] = s.lower() in ans
    for s in exp["must_not_contain"]:
        checks[f"avoids '{s}'"] = s.lower() not in ans
    for key, want in exp["expected_state"].items():
        got = len(trace["final_state"].get(key, []))
        checks[f"{key} == {want}"] = got == want
    failed = [k for k, ok in checks.items() if not ok]
    return {"passed": not failed, "checks": checks, "failed": failed}


if __name__ == "__main__":
    version = get_version()
    header(f"STEP 2: Task success — agent {version}")
    by_cat = defaultdict(lambda: [0, 0])
    total_pass = 0
    results = run_suite(version)
    for case, trace in results:
        r = evaluate_task(case, trace)
        total_pass += r["passed"]
        by_cat[case["category"]][0] += r["passed"]
        by_cat[case["category"]][1] += 1
        print(f"\n[{mark(r['passed'])}] {case['id']}: {case['input']}")
        print(f"       answer: {trace['answer'].replace(chr(10), ' / ')[:110]}")
        for f in r["failed"]:
            print(f"       ✗ {f}")

    print("\nSuccess by category:")
    for cat, (p, n) in sorted(by_cat.items()):
        print(f"  {cat:<15} {p}/{n}")
    print(f"\nTASK SUCCESS RATE: {total_pass}/{len(results)} = {total_pass/len(results):.0%}")
