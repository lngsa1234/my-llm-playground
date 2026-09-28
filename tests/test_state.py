from pathlib import Path

from core.state_manager import RUNS_DIRECTORY, load_state, new_goal_state, save_state


def test_state_round_trips(tmp_path):
    state = new_goal_state("Create a specification")
    save_state(state, tmp_path)
    assert load_state(state["goal_id"], tmp_path)["goal"] == "Create a specification"


def test_default_runs_directory_is_inside_the_project():
    assert RUNS_DIRECTORY == Path(__file__).resolve().parents[1] / "runs"
