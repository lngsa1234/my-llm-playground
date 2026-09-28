"""Demo 3: controlled end-to-end benchmark for goal context strategies."""

from __future__ import annotations

import os

import streamlit as st

from core.context_builder import build_goal_context
from core.evaluator import validate_final_output, validate_response
from core.llm_client import execute_goal_call
from core.state_manager import WORKFLOW, add_feedback, new_goal_state, utc_now


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


def run_controlled_benchmark(model: str, output_tokens: int, goal: str, selected: list[str]) -> dict:
    """Run independent sessions; state and artifacts are never shared across strategies."""
    sessions: dict[str, dict] = {}
    for label in selected:
        state = new_goal_state(goal, STRATEGIES[label])
        trace: list[dict] = []
        for step, ((operation, _), feedback) in enumerate(zip(WORKFLOW, CONTROLLED_EVENTS), start=1):
            if feedback:
                state = add_feedback(state, feedback)
            context = build_goal_context(state, feedback, token_budget=3500)
            result = execute_goal_call(model, context["context"], operation, output_tokens)
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


def _cost(metrics: list[dict], input_price: float, output_price: float) -> float:
    return (
        sum(item["input_tokens"] for item in metrics) * input_price
        + sum(item["output_tokens"] for item in metrics) * output_price
    ) / 1_000_000


def render_demo3() -> None:
    st.header("Demo 3 · Multi-Strategy Goal Benchmark")
    st.caption("Run the same six-event goal replay in independent sessions and compare end-to-end context choices.")
    st.info(
        "Each strategy starts from a new state and cannot access another strategy’s messages or artifacts. "
        "Only context construction changes; the goal, model, events, and output limit are fixed."
    )
    with st.expander("How this benchmark works", expanded=True):
        st.markdown(
            "Demo 3 is a **controlled replay**, not a live conversation like Demo 2. It applies the same "
            "predefined user feedback at each run to every strategy. After each event, the agent generates "
            "a response, and that response is saved only in that strategy’s own history and artifacts. "
            "This makes the comparison fair: the feedback is identical, while the context available to the "
            "agent differs."
        )
        st.markdown(
            "1. Start each strategy with a fresh copy of the goal.\n"
            "2. Apply the same fixed user event.\n"
            "3. Build that strategy’s context and call the agent.\n"
            "4. Save the response only in that strategy’s session, then repeat."
        )
    setup, controls = st.columns([2, 1])
    with setup:
        goal = st.text_area("Controlled benchmark goal", DEFAULT_GOAL, key="demo3_goal", height=110)
        selected = st.multiselect(
            "Strategies", list(STRATEGIES), default=list(STRATEGIES), key="demo3_strategies"
        )
        with st.expander("Fixed events supplied to every strategy"):
            st.dataframe(
                [
                    {"Run": number, "Agent operation": WORKFLOW[number - 1][0], "User event": event or "Initial goal"}
                    for number, event in enumerate(CONTROLLED_EVENTS, start=1)
                ],
                use_container_width=True,
                hide_index=True,
            )
    with controls:
        model = st.text_input("Model", "gpt-5.4-mini", key="demo3_model")
        output_tokens = st.number_input("Max output tokens", 200, 4000, 900, 100, key="demo3_output_tokens")
        input_price = st.number_input("Input $ / 1M", 0.0, 0.75, format="%.4f", key="demo3_in_price")
        output_price = st.number_input("Output $ / 1M", 0.0, 4.50, format="%.4f", key="demo3_out_price")
    if st.button("Run controlled benchmark", type="primary", key="demo3_run"):
        if not goal.strip() or not selected:
            st.warning("Enter a goal and select at least one strategy.")
        elif not os.getenv("OPENAI_API_KEY"):
            st.error("OPENAI_API_KEY is not configured.")
        else:
            try:
                with st.spinner(f"Running {len(selected)} independent sessions × {len(WORKFLOW)} calls…"):
                    st.session_state.demo3_results = run_controlled_benchmark(
                        model, int(output_tokens), goal.strip(), selected
                    )
            except Exception as exc:
                st.error(f"Benchmark stopped: {exc}")
    results = st.session_state.get("demo3_results", {})
    if not results:
        return

    rows = []
    chart_rows = []
    for label, session in results.items():
        metrics = session["state"]["metrics"]
        validation = session["validation"]
        rows.append(
            {
                "Strategy": label,
                "Requirement coverage": f"{validation['requirements_covered']} / {validation['requirements_total']}",
                "Validation": "Pass" if validation["valid"] else "Needs review",
                "Input tokens": sum(item["input_tokens"] for item in metrics),
                "Output tokens": sum(item["output_tokens"] for item in metrics),
                "Latency (s)": round(sum(item["latency_seconds"] for item in metrics), 2),
                "Estimated cost": f"${_cost(metrics, input_price, output_price):.5f}",
            }
        )
        for run in session["trace"]:
            chart_rows.append(
                {"Run": run["run"], "Strategy": label, "Estimated input tokens": run["context"]["estimated_input_tokens"]}
            )
    st.subheader("Final comparison")
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.subheader("Context growth by run")
    st.line_chart(chart_rows, x="Run", y="Estimated input tokens", color="Strategy", use_container_width=True)
    st.subheader("Independent session inspector")
    tabs = st.tabs(list(results))
    for tab, (label, session) in zip(tabs, results.items()):
        with tab:
            validation = session["validation"]
            st.caption(f"Final validation: {'Pass' if validation['valid'] else 'Needs review'} · {validation['requirements_covered']} of {validation['requirements_total']} approved requirements covered")
            for run in session["trace"]:
                with st.expander(f"Run {run['run']} · {run['operation']} — {run['feedback'][:60]}"):
                    st.markdown("**Constructed context**")
                    st.json(run["context"]["context"])
                    st.markdown("**Agent response**")
                    st.markdown(run["response"])
