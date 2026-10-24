"""Week 2 Demo 3 core logic: a controlled replay comparing goal context strategies."""

from __future__ import annotations

from core.common import ModelSettings
from core.week2.context_builder import build_goal_context
from core.week2.evaluator import validate_final_output, validate_response
from core.week2.llm_client import execute_goal_call
from core.week2.state_manager import WORKFLOW, add_feedback, new_goal_state, utc_now


DEFAULT_GOAL = (
    "Design a REST API for a task management system. Support creating tasks, "
    "updating task status, retrieving tasks, and soft deletion. Generate an API "
    "specification and a test plan."
)

# Every strategy receives exactly the same change at exactly the same run.
CONTROLLED_EVENTS = [
    "",
    "Task IDs must be globally unique. Statuses are todo, in_progress, and done.",
    "Use bearer-token authentication and include pagination for task retrieval.",
    "Deletion must be soft deletion; explain how deleted tasks are handled.",
    "Produce a final implementation specification with error behavior and edge cases.",
    "Validate the specification and provide a practical test plan.",
]

STRATEGIES = {
    "Full history": "full",
    "Recent window": "recent",
    "Summary + recent": "summary",
    "Structured + retrieval + recent": "structured",
}


def _record_response(state: dict, result: dict, context: dict, operation: str) -> None:
    step = state["current_step"] + 1
    state["artifacts"][f"{step}_{operation.lower()}"] = result["text"]
    state["history"].append({"role": "assistant", "kind": operation.lower(), "content": result["text"], "at": utc_now()})
    state["metrics"].append(
        {**result, "step": step, "operation": operation, "estimated_input_tokens": context["estimated_input_tokens"]}
    )
    state["current_step"] = step
    state["summary"] = f"Completed {operation}; approved requirements: {[item['text'] for item in state['requirements']]}"


def run_controlled_benchmark(settings: ModelSettings, goal: str, selected: list[str]) -> dict:
    """Run independent sessions; state and artifacts are never shared across strategies."""
    sessions: dict[str, dict] = {}
    for label in selected:
        state = new_goal_state(goal, STRATEGIES[label])
        trace: list[dict] = []
        for step, ((operation, _), feedback) in enumerate(zip(WORKFLOW, CONTROLLED_EVENTS), start=1):
            if feedback:
                state = add_feedback(state, feedback)
            context = build_goal_context(state, feedback, token_budget=3500)
            result = execute_goal_call(settings.model, context["context"], operation, settings.max_output_tokens)
            if not validate_response(result["text"])["valid"]:
                raise RuntimeError(f"{label}, run {step}: model returned no visible text")
            _record_response(state, result, context, operation)
            trace.append(
                {
                    "run": step,
                    "operation": operation,
                    "feedback": feedback or "Initial goal",
                    "context": context,
                    "response": result["text"],
                    "metrics": result,
                }
            )
        final_response = state["history"][-1]["content"]
        sessions[label] = {
            "state": state,
            "trace": trace,
            "validation": validate_final_output(state, final_response),
        }
    return sessions


def comparison_rows(results: dict, settings: ModelSettings) -> tuple[list[dict], list[dict]]:
    """Summary table and per-run context growth for the UI."""
    rows, chart_rows = [], []
    for label, session in results.items():
        metrics = session["state"]["metrics"]
        validation = session["validation"]
        total_in = sum(item["input_tokens"] for item in metrics)
        total_out = sum(item["output_tokens"] for item in metrics)
        rows.append({
            "Strategy": label,
            "Requirement coverage": f"{validation['requirements_covered']} / {validation['requirements_total']}",
            "Validation": "Pass" if validation["valid"] else "Needs review",
            "Input tokens": total_in,
            "Output tokens": total_out,
            "Latency (s)": round(sum(item["latency_seconds"] for item in metrics), 2),
            "Estimated cost": f"${settings.cost(total_in, total_out):.5f}",
        })
        for run in session["trace"]:
            chart_rows.append({"Run": run["run"], "Strategy": label, "Estimated input tokens": run["context"]["estimated_input_tokens"]})
    return rows, chart_rows
