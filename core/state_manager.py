"""Durable state for the Week 2 multi-run goal builder."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

# Resolve storage from this module rather than the terminal directory that
# launched Streamlit, so Demo 2 always writes inside this repository.
RUNS_DIRECTORY = Path(__file__).resolve().parent.parent / "runs"

WORKFLOW = [
    ("Understand", "Extract the goal's requirements, constraints, assumptions, and open questions."),
    ("Plan", "Create ordered subtasks and measurable success criteria."),
    ("Design", "Produce the primary design/specification artifact."),
    ("Refine", "Incorporate user feedback and update the design."),
    ("Validate", "Find missing requirements, conflicts, risks, and unresolved questions."),
    ("Finalize", "Deliver the final specification and a practical test plan."),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_goal_state(goal: str, strategy: str = "structured") -> dict:
    """Create a state document. Approved requirements are always human supplied."""
    return {
        "goal_id": f"goal-{uuid4().hex[:8]}",
        "goal": goal.strip(),
        "strategy": strategy,
        "status": "in_progress",
        "current_step": 0,
        "requirements": [],
        "decisions": [],
        "open_questions": [],
        "artifacts": {},
        "history": [],
        "summary": "",
        "validation_results": [],
        "metrics": [],
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }


def state_path(goal_id: str, runs_directory: Path = RUNS_DIRECTORY) -> Path:
    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "", goal_id)
    if not safe_id:
        raise ValueError("Invalid goal ID")
    return runs_directory / f"{safe_id}.json"


def save_state(state: dict, runs_directory: Path = RUNS_DIRECTORY) -> Path:
    runs_directory.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = utc_now()
    path = state_path(state["goal_id"], runs_directory)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return path


def load_state(goal_id: str, runs_directory: Path = RUNS_DIRECTORY) -> dict:
    path = state_path(goal_id, runs_directory)
    if not path.exists():
        raise FileNotFoundError(f"No saved goal named {goal_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def list_states(runs_directory: Path = RUNS_DIRECTORY) -> list[dict]:
    if not runs_directory.exists():
        return []
    states = []
    for path in runs_directory.glob("goal-*.json"):
        try:
            states.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return sorted(states, key=lambda item: item.get("updated_at", ""), reverse=True)


def add_feedback(state: dict, feedback: str) -> dict:
    """Record feedback as an approved requirement; it survives every model run."""
    updated = deepcopy(state)
    text = feedback.strip()
    if text:
        updated["requirements"].append({"text": text, "source": "user", "approved_at": utc_now()})
        updated["history"].append({"role": "user", "kind": "feedback", "content": text, "at": utc_now()})
    return updated
