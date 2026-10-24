from core.week2.goal_workflow import complete_goal, record_agent_response, user_declared_complete
from core.week2.state_manager import WORKFLOW, new_goal_state


def test_six_agent_responses_do_not_complete_a_goal():
    state = new_goal_state("Build an API")
    context = {"estimated_input_tokens": 10}
    result = {"text": "Agent response", "input_tokens": 10, "output_tokens": 5, "total_tokens": 15}
    for _ in WORKFLOW:
        state = record_agent_response(state, result, context, "Continue")
    assert state["current_step"] == len(WORKFLOW)
    assert state["status"] == "in_progress"


def test_only_an_explicit_user_completion_statement_ends_a_goal():
    state = new_goal_state("Build an API")
    assert user_declared_complete("This is finished")
    assert not user_declared_complete("Finish the soft-delete endpoint")
    completed = complete_goal(state, "This is finished")
    assert completed["status"] == "complete"
