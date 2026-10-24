"""Week 2 Demo 2 core logic: a persistent, multi-run goal builder."""

from __future__ import annotations

from labs.shared.settings import ModelSettings
from labs.week2_context_engineering.context_builder import build_goal_context
from labs.week2_context_engineering.evaluator import validate_final_output, validate_response
from labs.week2_context_engineering.llm_client import execute_goal_call
from labs.week2_context_engineering.state_manager import WORKFLOW, add_feedback, new_goal_state, save_state, utc_now

CONTEXT_TOKEN_BUDGET = 3500
COMPLETION_MESSAGES = {
    "done", "finished", "complete", "this is done", "this is finished", "this is complete",
    "the goal is done", "the goal is finished", "the goal is complete", "we are done", "were done",
}


def record_agent_response(state: dict, result: dict, context: dict, operation: str, feedback: str = "") -> dict:
    """Persist one successful agent response and advance the hidden workflow."""
    if feedback.strip():
        state = add_feedback(state, feedback)
    step = state["current_step"] + 1
    state["artifacts"][f"{step}_{operation.lower()}"] = result["text"]
    state["history"].append({"role": "assistant", "kind": operation.lower(), "content": result["text"], "at": utc_now()})
    state["metrics"].append({**result, "step": step, "operation": operation, "estimated_input_tokens": context["estimated_input_tokens"]})
    state["current_step"] = step
    state["status"] = "in_progress"
    state["summary"] = f"Completed {operation}; approved requirements: {[x['text'] for x in state['requirements']]}"
    return state


def user_declared_complete(message: str) -> bool:
    """Only an explicit user statement, never workflow count, ends a goal."""
    normalized = " ".join(message.lower().replace("'", "").split())
    return normalized in COMPLETION_MESSAGES


def complete_goal(state: dict, user_message: str) -> dict:
    """Record the user's completion declaration and validate the latest agent response."""
    state["history"].append({"role": "user", "kind": "completion", "content": user_message.strip(), "at": utc_now()})
    state["status"] = "complete"
    state["summary"] = "The user declared this goal complete."
    latest_response = next((entry["content"] for entry in reversed(state["history"]) if entry["role"] == "assistant"), "")
    state["validation_results"].append(validate_final_output(state, latest_response))
    return state


def next_operation(state: dict) -> str:
    index = state["current_step"]
    return WORKFLOW[index][0] if index < len(WORKFLOW) else "Continue"


def preview_context(state: dict, note: str) -> dict:
    """The context the next agent call would receive, for inspection in the UI."""
    return build_goal_context(state, note, token_budget=CONTEXT_TOKEN_BUDGET)


def start_goal(settings: ModelSettings, goal: str) -> dict:
    """Create a new goal, run its first agent call, and save the state."""
    state = new_goal_state(goal, "structured")
    operation = WORKFLOW[0][0]
    context = preview_context(state, "")
    result = execute_goal_call(settings.model, context["context"], operation, settings.max_output_tokens)
    if not validate_response(result["text"])["valid"]:
        raise RuntimeError("The agent returned no visible text. The goal was not started.")
    state = record_agent_response(state, result, context, operation)
    save_state(state)
    return state


def run_goal_step(settings: ModelSettings, state: dict, note: str) -> dict:
    """Apply the user's feedback (or completion), run one agent call, and save the state."""
    if user_declared_complete(note):
        state = complete_goal(state, note)
    else:
        operation = next_operation(state)
        context = preview_context(state, note)
        result = execute_goal_call(settings.model, context["context"], operation, settings.max_output_tokens)
        if not validate_response(result["text"])["valid"]:
            raise RuntimeError("Step was not saved because the model returned no visible text.")
        state = record_agent_response(state, result, context, operation, note)
    save_state(state)
    return state


def run_totals(state: dict, settings: ModelSettings) -> dict:
    metrics = state["metrics"]
    total_in = sum(x["input_tokens"] for x in metrics)
    total_out = sum(x["output_tokens"] for x in metrics)
    return {"calls": len(metrics), "input_tokens": total_in, "output_tokens": total_out,
            "cost": settings.cost(total_in, total_out)}
