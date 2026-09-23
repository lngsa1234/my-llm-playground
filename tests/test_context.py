from core.context_builder import build_goal_context
from core.state_manager import add_feedback, new_goal_state


def test_feedback_is_preserved_as_approved_requirement():
    state = add_feedback(new_goal_state("Build an API"), "IDs must be unique")
    assert state["requirements"][0]["text"] == "IDs must be unique"
    assert state["requirements"][0]["source"] == "user"


def test_recent_context_respects_budget():
    state = new_goal_state("Build an API", "recent")
    state["history"] = [{"role": "assistant", "content": "x" * 500} for _ in range(20)]
    result = build_goal_context(state, "continue", token_budget=300)
    assert result["estimated_input_tokens"] <= 300


def test_structured_context_contains_old_approved_requirement():
    state = add_feedback(new_goal_state("Build an API", "structured"), "Use soft deletion")
    state["history"] = [{"role": "assistant", "content": "unrelated"} for _ in range(10)]
    result = build_goal_context(state, "design it")
    assert result["context"]["approved_requirements"][0]["text"] == "Use soft deletion"
