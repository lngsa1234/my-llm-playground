"""Week 6 core logic: agent evaluation for the Streamlit app.

The command-line lab in this folder (lab/, data/, run_all.py) stays a standalone, standard-library
project that learners can run from the command line. This module loads its
code (the Muse agent, golden dataset and the five evaluation steps) so the app
and the command line always grade the same way, and adds an LLM judge that
uses the app's ⚙️ Model settings.
"""

from __future__ import annotations

import importlib
import json
import re
import sys
import time
from pathlib import Path
from typing import Callable

from openai import OpenAI

from labs.shared.settings import ModelSettings

LAB_DIR = Path(__file__).resolve().parent / "lab"

if str(LAB_DIR) not in sys.path:
    sys.path.insert(0, str(LAB_DIR))
agent = importlib.import_module("agent")
lab_common = importlib.import_module("common")
golden = importlib.import_module("step1_golden")
task_step = importlib.import_module("step2_task_success")
tool_step = importlib.import_module("step3_tool_eval")
judge_step = importlib.import_module("step4_llm_judge")

VERSIONS = ["v1", "v2"]
VERSION_LABELS = {"v1": "v1 · production baseline", "v2": "v2 · “faster, friendlier” candidate"}
RUBRIC = judge_step.RUBRIC
DIMENSIONS = ["task", "tools", "judge"]
DEFAULT_GATES = {"max_safety_violations": 0, "max_new_failures": 0, "max_metric_drop": 0.05}

Judge = Callable[[dict], dict]


# ------------------------------------------------------------ data + agent
def load_cases() -> list[dict]:
    return lab_common.load_golden()


def run_agent(query: str, version: str) -> dict:
    return agent.run_agent(query, version).to_dict()


def run_suite(version: str) -> list[tuple[dict, dict]]:
    return lab_common.run_suite(version)


def grade_case(case: dict, version: str) -> dict:
    """Run one golden case and grade it the way steps 2 and 3 do."""
    trace = run_agent(case["input"], version)
    task = task_step.evaluate_task(case, trace)
    tools = tool_step.evaluate_tools(case, trace)
    tool_problems = tools["arg_errors"] + [f"forbidden tool called: {f}" for f in tools["forbidden_calls"]]
    if not tools["order_ok"] and not tool_problems:
        tool_problems.append(f"expected path {' → '.join(tools['expected']) or '(no tools)'}")
    return {"trace": trace, "task_passed": task["passed"], "task_failed": task["failed"],
            "tools_passed": tools["passed"], "tool_problems": tool_problems}


# ------------------------------------------------------- step 1: dataset
def dataset_report(cases: list[dict]) -> dict:
    problems, warnings = golden.lint(cases)
    categories, difficulty, side_effects = golden.coverage(cases)
    return {"problems": problems, "warnings": warnings, "categories": dict(categories),
            "difficulty": dict(difficulty), "side_effect_cases": side_effects,
            "hard_share": difficulty.get("hard", 0) / len(cases) if cases else 0.0}


# --------------------------------------------------- step 2: task success
def task_results(version: str) -> tuple[list[dict], float]:
    rows = []
    for case, trace in run_suite(version):
        r = task_step.evaluate_task(case, trace)
        rows.append({"Case": case["id"], "Category": case["category"], "Input": case["input"],
                     "Result": "PASS" if r["passed"] else "FAIL", "Failed checks": "; ".join(r["failed"]),
                     "Answer": trace["answer"]})
    return rows, sum(r["Result"] == "PASS" for r in rows) / len(rows)


# --------------------------------------------------- step 3: tool use
def tool_results(version: str) -> tuple[list[dict], dict]:
    rows, agg = [], {"precision": 0.0, "recall": 0.0, "order": 0, "args": 0, "safety_violations": 0, "pass": 0}
    results = run_suite(version)
    for case, trace in results:
        r = tool_step.evaluate_tools(case, trace)
        agg["precision"] += r["precision"]
        agg["recall"] += r["recall"]
        agg["order"] += r["order_ok"]
        agg["args"] += not r["arg_errors"]
        agg["safety_violations"] += len(r["forbidden_calls"])
        agg["pass"] += r["passed"]
        rows.append({"Case": case["id"], "Result": "PASS" if r["passed"] else "FAIL",
                     "Expected path": " → ".join(r["expected"]) or "(no tools)",
                     "Actual path": " → ".join(r["called"]) or "(no tools)",
                     "Problems": "; ".join(r["arg_errors"] + [f"FORBIDDEN: {f}" for f in r["forbidden_calls"]])})
    n = len(results)
    summary = {"precision": agg["precision"] / n, "recall": agg["recall"] / n, "order": agg["order"] / n,
               "args": agg["args"] / n, "safety_violations": agg["safety_violations"], "pass_rate": agg["pass"] / n}
    return rows, summary


# --------------------------------------------------- step 4: judge
def heuristic_judge(trace: dict) -> dict:
    """The lab's deterministic stand-in judge: offline, free, same answer every time."""
    return judge_step.mock_judge(trace)


def llm_judge(settings: ModelSettings, usage: dict | None = None) -> Judge:
    """A judge that sends the lab's rubric prompt to the model in ⚙️ Model settings."""
    client = OpenAI()

    def judge(trace: dict) -> dict:
        response = client.responses.create(model=settings.model, input=judge_step.build_prompt(trace),
                                           max_output_tokens=settings.max_output_tokens)
        if usage is not None:
            usage["calls"] = usage.get("calls", 0) + 1
            usage["input_tokens"] = usage.get("input_tokens", 0) + response.usage.input_tokens
            usage["output_tokens"] = usage.get("output_tokens", 0) + response.usage.output_tokens
        match = re.search(r"\{.*\}", response.output_text or "", re.S)
        if not match:
            raise ValueError(f"The judge did not return JSON: {response.output_text!r:.200}")
        scores = json.loads(match.group(0))
        return {**{k: int(scores[k]) for k in RUBRIC}, "reasoning": str(scores.get("reasoning", ""))}

    return judge


def judge_prompt_example(version: str = "v1") -> str:
    _, trace = run_suite(version)[0]
    return judge_step.build_prompt(trace)


def judge_results(version: str, judge: Judge) -> dict:
    labels = judge_step.load_human_labels().get(version, {})
    rows, totals, agree, labeled = [], {k: 0 for k in RUBRIC}, 0, 0
    started = time.perf_counter()
    for case, trace in run_suite(version):
        scores = judge(trace)
        passed = judge_step.judge_passes(scores)
        for k in RUBRIC:
            totals[k] += scores[k]
        human = labels.get(case["id"])
        if human:
            labeled += 1
            agree += human["pass"] == passed
        rows.append({"Case": case["id"], "Judge": "PASS" if passed else "FAIL",
                     **{k.title(): scores[k] for k in RUBRIC}, "Reasoning": scores["reasoning"],
                     "Human label": "" if not human else ("PASS" if human["pass"] else "FAIL"),
                     "Agrees": "" if not human else ("✓" if human["pass"] == passed else "⚠"),
                     "Human note": human["why"] if human else ""})
    n = len(rows)
    return {"rows": rows, "averages": {k: totals[k] / n for k in RUBRIC},
            "pass_rate": sum(r["Judge"] == "PASS" for r in rows) / n,
            "agreement": agree / labeled if labeled else None, "labeled": labeled,
            "seconds": time.perf_counter() - started}


# --------------------------------------------------- step 5: regression
def full_eval(version: str, judge: Judge) -> dict:
    per_case, safety = {}, 0
    for case, trace in run_suite(version):
        t = task_step.evaluate_task(case, trace)
        tl = tool_step.evaluate_tools(case, trace)
        j = judge(trace)
        safety += len(tl["forbidden_calls"])
        per_case[case["id"]] = {
            "task": t["passed"], "tools": tl["passed"], "judge": judge_step.judge_passes(j),
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


def regression(baseline: str, candidate: str, judge: Judge, gates: dict = DEFAULT_GATES) -> dict:
    base, cand = full_eval(baseline, judge), full_eval(candidate, judge)
    new_failures, fixed = [], []
    for cid, c in cand["cases"].items():
        b = base["cases"].get(cid)
        if b is None:
            continue
        for d in DIMENSIONS:
            if b[d] and not c[d]:
                new_failures.append({"Case": cid, "Dimension": d, "Why": "; ".join(c["why"][d])})
            elif not b[d] and c[d]:
                fixed.append({"Case": cid, "Dimension": d})
    drops = {d: base["metrics"][d] - cand["metrics"][d] for d in DIMENSIONS}
    gate_results = {
        f"Safety violations ≤ {gates['max_safety_violations']}": cand["metrics"]["safety_violations"] <= gates["max_safety_violations"],
        f"New failures ≤ {gates['max_new_failures']}": len(new_failures) <= gates["max_new_failures"],
        f"No metric drops more than {gates['max_metric_drop']:.0%}": all(v <= gates["max_metric_drop"] for v in drops.values()),
    }
    return {"base": base, "cand": cand, "new_failures": new_failures, "fixed": fixed,
            "gates": gate_results, "ship": all(gate_results.values())}


def regression_report(result: dict) -> str:
    """Markdown summary, ready to paste into a pull request."""
    base, cand = result["base"], result["cand"]
    lines = [f"# Regression report: {base['version']} → {cand['version']}", "",
             "| Metric | Baseline | Candidate | Δ |", "|---|---|---|---|"]
    for d in DIMENSIONS:
        b, c = base["metrics"][d], cand["metrics"][d]
        lines.append(f"| {d} pass rate | {b:.0%} | {c:.0%} | {c - b:+.0%} |")
    lines.append(f"| safety violations | {base['metrics']['safety_violations']} | {cand['metrics']['safety_violations']} | |")
    lines += ["", "## Gates"] + [f"- {'✅' if ok else '❌'} {g}" for g, ok in result["gates"].items()]
    lines += ["", f"**Verdict: {'SHIP IT ✅' if result['ship'] else 'BLOCK RELEASE ❌'}**", "", "## New failures"]
    lines += [f"- **{f['Case']}** ({f['Dimension']}): {f['Why']}" for f in result["new_failures"]] or ["- none"]
    lines += ["", "## Fixed"] + ([f"- {f['Case']} ({f['Dimension']})" for f in result["fixed"]] or ["- none"])
    return "\n".join(lines) + "\n"
