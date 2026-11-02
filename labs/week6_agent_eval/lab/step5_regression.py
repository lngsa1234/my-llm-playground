"""
STEP 5 — REGRESSION TESTING
Question: did the new version break anything that used to work?
We run ALL the evals (task + tools + judge) on a baseline and on a candidate,
diff them case by case, and apply release GATES. Exit code 1 = block the
release, so this drops straight into CI.

Run:  python3 lab/step5_regression.py --baseline v1   # save a baseline
      python3 lab/step5_regression.py v2              # compare candidate
"""
import json
import os
import sys

from common import RESULTS, get_version, header, run_suite, save_json
from step2_task_success import evaluate_task
from step3_tool_eval import evaluate_tools
from step4_llm_judge import RUBRIC, judge_passes, mock_judge

# Release gates -- tune these for your product
GATES = {
    "max_safety_violations": 0,      # hard rule: zero forbidden tool calls
    "max_new_failures": 0,           # no case may go pass -> fail
    "max_metric_drop": 0.05,         # no aggregate metric may drop > 5 points
}
DIMENSIONS = ["task", "tools", "judge"]


def full_eval(version):
    per_case, safety = {}, 0
    for case, trace in run_suite(version):
        t = evaluate_task(case, trace)
        tl = evaluate_tools(case, trace)
        j = mock_judge(trace)
        safety += len(tl["forbidden_calls"])
        per_case[case["id"]] = {
            "task": t["passed"], "tools": tl["passed"], "judge": judge_passes(j),
            "judge_scores": {k: j[k] for k in RUBRIC},
            "why": {
                "task": t["failed"],
                "tools": tl["arg_errors"] + [f"forbidden: {f}" for f in tl["forbidden_calls"]]
                         + ([] if tl["order_ok"] else [f"path {tl['called']} != {tl['expected']}"]),
                "judge": [j["reasoning"]],
            },
        }
    n = len(per_case)
    metrics = {d: sum(c[d] for c in per_case.values()) / n for d in DIMENSIONS}
    metrics["safety_violations"] = safety
    return {"version": version, "metrics": metrics, "cases": per_case}


def compare(base, cand):
    new_fail, fixed = [], []
    for cid, c in cand["cases"].items():
        b = base["cases"].get(cid)
        if b is None:
            continue
        for d in DIMENSIONS:
            if b[d] and not c[d]:
                new_fail.append((cid, d, c["why"][d]))
            elif not b[d] and c[d]:
                fixed.append((cid, d))
    drops = {d: base["metrics"][d] - cand["metrics"][d] for d in DIMENSIONS}
    gates = {
        "safety violations": cand["metrics"]["safety_violations"] <= GATES["max_safety_violations"],
        "no new failures": len(new_fail) <= GATES["max_new_failures"],
        "no big metric drop": all(v <= GATES["max_metric_drop"] for v in drops.values()),
    }
    return new_fail, fixed, drops, gates


def write_report(base, cand, new_fail, fixed, gates):
    lines = [f"# Regression report: {base['version']} → {cand['version']}", "",
             "| Metric | Baseline | Candidate | Δ |", "|---|---|---|---|"]
    for d in DIMENSIONS:
        b, c = base["metrics"][d], cand["metrics"][d]
        lines.append(f"| {d} pass rate | {b:.0%} | {c:.0%} | {c - b:+.0%} |")
    lines.append(f"| safety violations | {base['metrics']['safety_violations']} | "
                 f"{cand['metrics']['safety_violations']} | |")
    lines += ["", "## Gates"] + [f"- {'✅' if ok else '❌'} {g}" for g, ok in gates.items()]
    lines += ["", "## New failures"] + ([f"- **{cid}** ({d}): {'; '.join(w)}"
                                         for cid, d, w in new_fail] or ["- none"])
    lines += ["", "## Fixed"] + ([f"- {cid} ({d})" for cid, d in fixed] or ["- none"])
    path = os.path.join(RESULTS, "regression_report.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path


if __name__ == "__main__":
    baseline_path = os.path.join(RESULTS, "baseline.json")

    if "--baseline" in sys.argv:
        v = get_version("v1")
        res = full_eval(v)
        save_json("baseline.json", res)
        header(f"Saved baseline from agent {v}")
        print(json.dumps(res["metrics"], indent=2))
        sys.exit(0)

    if not os.path.exists(baseline_path):
        print("No baseline found -- creating one from v1 first.")
        save_json("baseline.json", full_eval("v1"))
    with open(baseline_path, encoding="utf-8") as f:
        base = json.load(f)

    cand = full_eval(get_version("v2"))
    save_json(f"candidate_{cand['version']}.json", cand)
    new_fail, fixed, drops, gates = compare(base, cand)

    header(f"STEP 5: Regression — baseline {base['version']} vs candidate {cand['version']}")
    print(f"\n{'metric':<18}{'baseline':>10}{'candidate':>11}{'delta':>9}")
    for d in DIMENSIONS:
        b, c = base["metrics"][d], cand["metrics"][d]
        arrow = "▼" if c < b else ("▲" if c > b else " ")
        print(f"{d + ' pass rate':<18}{b:>10.0%}{c:>11.0%}{c - b:>+8.0%} {arrow}")
    print(f"{'safety violations':<18}{base['metrics']['safety_violations']:>10}"
          f"{cand['metrics']['safety_violations']:>11}")

    print(f"\nNew failures ({len(new_fail)}):")
    for cid, d, why in new_fail:
        print(f"  ✗ {cid:<8} [{d}] {'; '.join(why)[:100]}")
    print(f"Fixed ({len(fixed)}):", ", ".join(f"{c}[{d}]" for c, d in fixed) or "none")

    print("\nRelease gates:")
    for g, ok in gates.items():
        print(f"  {'✅' if ok else '❌'} {g}")
    report = write_report(base, cand, new_fail, fixed, gates)
    verdict = all(gates.values())
    print(f"\nVERDICT: {'SHIP IT ✅' if verdict else 'BLOCK RELEASE ❌'}   (report: {os.path.relpath(report)})")
    sys.exit(0 if verdict else 1)
