"""Explicit, inspectable context construction for multi-run goals."""

from __future__ import annotations

import json
from typing import Any


def estimate_tokens(value: Any) -> int:
    """Conservative dependency-free estimate, suitable for enforcing a UI budget."""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return max(1, (len(text) + 3) // 4)


def _clip(items: list[dict], budget: int) -> list[dict]:
    chosen: list[dict] = []
    spent = 0
    for item in reversed(items):
        item_tokens = estimate_tokens(item)
        if chosen and spent + item_tokens > budget:
            break
        chosen.append(item)
        spent += item_tokens
    return list(reversed(chosen))


def _summary(state: dict) -> str:
    requirements = [item["text"] for item in state.get("requirements", [])]
    decisions = state.get("decisions", [])
    artifacts = list(state.get("artifacts", {}).keys())
    return (
        f"Goal: {state['goal']}\n"
        f"Approved requirements: {requirements or ['None yet']}\n"
        f"Decisions: {decisions or ['None yet']}\n"
        f"Completed artifacts: {artifacts or ['None yet']}\n"
        f"Open questions: {state.get('open_questions', []) or ['None yet']}"
    )


def _relevant_artifacts(artifacts: dict[str, str], query: str, limit: int = 2) -> dict[str, str]:
    """Select prior artifacts with simple, inspectable keyword retrieval."""
    terms = {word.lower().strip(".,:;()[]") for word in query.split() if len(word) > 3}
    ranked = sorted(
        artifacts.items(),
        key=lambda item: len(terms & set(item[1].lower().split())),
        reverse=True,
    )
    return dict(ranked[:limit])


def build_goal_context(state: dict, user_message: str, token_budget: int = 3500) -> dict:
    """Build model input and provenance without mutating the persisted state."""
    base = {
        "goal": state["goal"],
        "workflow_step": state["current_step"] + 1,
        "approved_requirements": state.get("requirements", []),
        "approved_decisions": state.get("decisions", []),
        "user_message": user_message.strip() or "Continue the workflow using the approved state.",
    }
    strategy = state.get("strategy", "structured")
    history = state.get("history", [])
    provenance = ["goal", "approved_requirements", "approved_decisions", "user_message"]

    if strategy == "full":
        base["history"] = _clip(history, max(250, token_budget - estimate_tokens(base)))
        provenance.append("history (latest entries retained to fit budget)")
    elif strategy == "recent":
        base["recent_history"] = _clip(history[-6:], max(250, token_budget - estimate_tokens(base)))
        provenance.append("last 6 history entries")
    elif strategy == "summary":
        base["state_summary"] = state.get("summary") or _summary(state)
        base["recent_history"] = _clip(history[-4:], max(250, token_budget - estimate_tokens(base)))
        provenance.extend(["structured state summary", "last 4 history entries"])
    else:
        base["state_summary"] = state.get("summary") or _summary(state)
        base["recent_history"] = _clip(history[-4:], max(250, token_budget - estimate_tokens(base)))
        base["relevant_artifacts"] = _relevant_artifacts(
            state.get("artifacts", {}), f"{state['goal']} {user_message}"
        )
        provenance.extend(["structured state summary", "last 4 history entries", "keyword-selected artifacts"])

    # Drop oldest optional content until the budget is honored.
    while estimate_tokens(base) > token_budget and base.get("recent_history"):
        base["recent_history"].pop(0)
    while estimate_tokens(base) > token_budget and base.get("history"):
        base["history"].pop(0)
    if estimate_tokens(base) > token_budget:
        base["state_summary"] = base.get("state_summary", "")[: max(0, token_budget * 3)]

    return {"context": base, "provenance": provenance, "estimated_input_tokens": estimate_tokens(base)}
