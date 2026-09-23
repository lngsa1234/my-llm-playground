from core.state_manager import load_state, new_goal_state, save_state


def test_state_round_trips(tmp_path):
    state = new_goal_state("Create a specification")
    save_state(state, tmp_path)
    assert load_state(state["goal_id"], tmp_path)["goal"] == "Create a specification"
