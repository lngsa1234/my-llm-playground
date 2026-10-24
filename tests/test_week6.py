from core.week6 import evals


def test_golden_dataset_loads_and_lints_clean():
    cases = evals.load_cases()
    report = evals.dataset_report(cases)
    assert len(cases) == 12
    assert report["problems"] == []


def test_v1_passes_task_and_tool_checks_and_v2_regresses():
    assert evals.task_results("v1")[1] == 1.0
    assert evals.task_results("v2")[1] == 0.75
    assert evals.tool_results("v1")[1]["safety_violations"] == 0
    assert evals.tool_results("v2")[1]["safety_violations"] == 3


def test_regression_blocks_v2_with_heuristic_judge():
    result = evals.regression("v1", "v2", evals.heuristic_judge)
    assert not result["ship"]
    assert len(result["new_failures"]) == 18
    assert "BLOCK RELEASE" in evals.regression_report(result)


def test_regression_ships_when_candidate_equals_baseline():
    result = evals.regression("v1", "v1", evals.heuristic_judge)
    assert result["ship"]
    assert result["new_failures"] == []
