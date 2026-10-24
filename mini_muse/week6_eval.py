"""Week 6 · Proof: grade the real Mini Muse with the Week 6 golden dataset.

The simulated Muse (v1, v2) gives the same answer every time, which made it easy to
learn the evaluation steps. Mini Muse is a real LLM agent, so two new things appear:

  variation   the same case can pass on one run and fail on the next. Run each case
              several times and report a pass *rate*; a case that sometimes fails is "flaky".
  brittleness keyword checks ("must contain 'Booked'") can fail a correct answer that is
              worded differently. Read the failures before blaming the agent: sometimes
              the test is what needs fixing.

Grading reuses the Week 6 steps unchanged (task success, tool use, and optionally the judge).
"""

from __future__ import annotations

from collections.abc import Callable

from labs.week6_agent_eval import evals

RunFn = Callable[[str], dict]


def load_cases(categories: list[str] | None = None) -> list[dict]:
    cases = evals.load_cases()
    return [c for c in cases if not categories or c["category"] in categories]


def mini_muse_runner(llm, **agent_options) -> RunFn:
    from mini_muse.week5_agent import run

    return lambda text: run(llm, text, **agent_options)


def grade(case: dict, trace: dict, judge: Callable[[dict], dict] | None = None) -> dict:
    task = evals.task_step.evaluate_task(case, trace)
    tools = evals.tool_step.evaluate_tools(case, trace)
    result = {"task": task["passed"], "tools": tools["passed"], "task_failed": task["failed"],
              "tool_path": " → ".join(tools["called"]) or "(no tools)",
              "tool_problems": tools["arg_errors"] + [f"forbidden: {f}" for f in tools["forbidden_calls"]]
                               + ([] if tools["order_ok"] else [f"expected {' → '.join(tools['expected']) or '(no tools)'}"]),
              "held_for_approval": [a["tool"] for a in trace.get("pending_actions", [])]}
    if judge:
        scores = judge(trace)
        result["judge"] = evals.judge_step.judge_passes(scores)
        result["judge_reason"] = scores.get("reasoning", "")
    return result


def run_golden(run_fn: RunFn, cases: list[dict], repeats: int = 1, judge=None,
               progress: Callable[[int, int], None] | None = None) -> dict:
    """Run every case `repeats` times. Returns per-case rows, overall rates and flaky cases."""
    rows, runs, total, done = [], [], len(cases) * repeats, 0
    for case in cases:
        graded = []
        for attempt in range(repeats):
            trace = run_fn(case["input"])
            g = grade(case, trace, judge)
            graded.append(g)
            runs.append({"Case": case["id"], "Run": attempt + 1, "Task": _mark(g["task"]), "Tools": _mark(g["tools"]),
                         "Tool path": g["tool_path"], "Held for approval": ", ".join(g["held_for_approval"]),
                         "Problems": "; ".join(g["task_failed"] + g["tool_problems"]), "Answer": trace["answer"]})
            done += 1
            if progress:
                progress(done, total)
        task_rate = sum(g["task"] for g in graded) / repeats
        tool_rate = sum(g["tools"] for g in graded) / repeats
        both = sum(g["task"] and g["tools"] for g in graded) / repeats
        rows.append({"Case": case["id"], "Category": case["category"], "Input": case["input"],
                     "Task pass": f"{task_rate:.0%}", "Tools pass": f"{tool_rate:.0%}",
                     "Status": "PASS" if both == 1 else "FAIL" if both == 0 else "FLAKY",
                     "v1 (simulated)": _v1_status(case)})
    n = len(runs) or 1
    return {"rows": rows, "runs": runs,
            "task_rate": sum(r["Task"] == "PASS" for r in runs) / n,
            "tool_rate": sum(r["Tools"] == "PASS" for r in runs) / n,
            "flaky": [r["Case"] for r in rows if r["Status"] == "FLAKY"],
            "failing": [r["Case"] for r in rows if r["Status"] == "FAIL"]}


def _mark(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


def _v1_status(case: dict) -> str:
    g = evals.grade_case(case, "v1")
    return "PASS" if g["task_passed"] and g["tools_passed"] else "FAIL"
