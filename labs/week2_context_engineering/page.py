"""Week 2 page: context engineering, in three demos.

Run alone:   streamlit run labs/week2_context_engineering/page.py
In the site: streamlit run app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Lets this page run on its own (streamlit run labs/<lab>/page.py) as well as inside app.py.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from labs.shared.settings import ModelSettings
from labs.week2_context_engineering import goal_replay, goal_workflow, strategy_benchmark as bench
from labs.week2_context_engineering.evaluator import validate_final_output
from labs.week2_context_engineering.longbench_subset import download_subset, load_cached_cases
from labs.week2_context_engineering.state_manager import WORKFLOW, load_state
from labs.shared.ui import mini_muse_part, can_run, lab_parameters, metric_row, model_settings, page_layout, show_error, run_standalone

HOW_IT_WORKS = """
- **Demo 1 · Strategy benchmark** — the same question is answered with five different contexts (none, full history, recent window, summary, keyword retrieval). Compare fact coverage, tokens and cost.
- **Demo 2 · Multi-run builder** — a goal is worked on across several calls. Each call rebuilds its context from saved state: the goal and approved requirements, a summary plus recent messages, and earlier artifacts.
- **Demo 3 · Controlled replay** — the same scripted feedback is replayed against several context strategies in separate sessions, so only the context construction differs.

All three use the model, max output tokens and prices from ⚙️ Model settings.
"""


DEMOS = ["Demo 1 · Strategy benchmark", "Demo 2 · Multi-run builder", "Demo 3 · Controlled replay"]


def render() -> None:
    main, panel = page_layout("Week 2 · Context Engineering",
                "Choose what the model sees on each call, and measure what that choice costs and changes.",
                HOW_IT_WORKS)
    if mini_muse_part(main, panel, 2):
        return
    settings = model_settings(panel)
    with lab_parameters(panel):
        demo = st.radio("Demo", DEMOS, key="week2_demo")
        st.divider()
        if demo == DEMOS[0]:
            params = _strategy_benchmark_parameters()
        elif demo == DEMOS[1]:
            params = _goal_builder_parameters()
        else:
            params = _goal_replay_parameters()
    with main:
        st.subheader(demo)
        if demo == DEMOS[0]:
            _render_strategy_benchmark(settings, params)
        elif demo == DEMOS[1]:
            _render_goal_builder(settings, params)
        else:
            _render_goal_replay(settings, params)


# ------------------------------------------------------------ Demo 1
def _strategy_benchmark_parameters() -> dict:
    dataset_name = st.selectbox("Dataset", list(bench.DATASETS) + [bench.OFFICIAL_DATASET], key="demo1_dataset")
    if dataset_name == bench.OFFICIAL_DATASET:
        cases = load_cached_cases()
        if cases is None:
            return {"needs_download": True}
        labels = [f"Question {i}: {case['input'][:58]}…" for i, case in enumerate(cases, start=1)]
        chosen = st.selectbox("HotpotQA question", range(len(cases)), format_func=lambda i: labels[i], key="demo1_longbench_case")
        dataset, case_key = bench.longbench_dataset(cases[chosen]), f"{dataset_name}_{chosen}"
    else:
        dataset, case_key = bench.DATASETS[dataset_name], dataset_name
    strategies = st.multiselect("Context strategies", bench.STRATEGIES,
                                default=[s for s in bench.STRATEGIES if s in bench.DEFAULT_STRATEGIES], key="demo1_strategies")
    return {"dataset": dataset, "case_key": case_key, "strategies": strategies}


def _render_strategy_benchmark(settings: ModelSettings, params: dict) -> None:
    st.caption("Run independent calls against one dataset, one per context strategy.")
    if params.get("needs_download"):
        st.info("This dataset downloads the official LongBench archive once (about 109 MB), then caches ten HotpotQA cases locally.")
        if st.button("Download official LongBench subset", key="demo1_download_longbench"):
            try:
                with st.spinner("Downloading and preparing the official subset…"):
                    download_subset()
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                show_error("LongBench download", exc)
        return
    dataset, case_key, strategies = params["dataset"], params["case_key"], params["strategies"]
    left, right = st.columns([0.9, 1.1], gap="large")
    with left:
        with st.expander("Dataset and expected facts"):
            for message_id, role, content in dataset["history"]:
                if role == "document":
                    with st.container(border=True):
                        st.caption(f"[{message_id}] Document passage")
                        st.write(content)
                else:
                    with st.chat_message(role):
                        st.write(f"[{message_id}] {role.title()}: {content}")
            st.dataframe([{"Requirement": name.title(), "Expected terms": ", ".join(words)}
                          for name, words in dataset["expected_facts"].items()], width="stretch", hide_index=True)
            if dataset.get("official"):
                st.caption(f"Official LongBench reference answer: {dataset['reference_answer']}")
        instruction = st.text_area("Benchmark instruction", dataset["instruction"], key=f"demo1_instruction_{case_key}", height=110)
        if st.button("Run benchmark", type="primary", disabled=not strategies, key="demo1_run", width="stretch"):
            if can_run(settings, instruction):
                status = st.empty()
                st.session_state.demo1_results = bench.run_strategy_benchmark(
                    settings, dataset, instruction, strategies, case_key, progress=lambda text: status.caption(text))
                status.empty()

    with right:
        results = [r for r in st.session_state.get("demo1_results", []) if r.get("case_key") == case_key]
        st.subheader("Results")
        if not results:
            st.info("Choose context strategies in 🧪 Lab parameters, then run the benchmark.")
            return
        metric_label = "Answer F1" if dataset.get("official") else "Fact coverage"
        st.dataframe([{
            "Strategy": r["strategy"], metric_label: f"{r.get('accuracy', 0):.0%}",
            "Evidence recall": f"{r['evidence_recall']:.0%}" if r.get("evidence_recall") is not None else "N/A",
            "Input": r.get("input_tokens", "—"), "Output": r.get("output_tokens", "—"),
            "Latency": f"{r.get('latency', 0):.2f}s", "Cost": f"${r.get('cost', 0):.5f}",
        } for r in results], width="stretch", hide_index=True)
        for tab, result in zip(st.tabs([r["strategy"] for r in results]), results):
            with tab:
                if "error" in result:
                    st.error(result["error"])
                else:
                    recall = f"{result['evidence_recall']:.0%}" if result["evidence_recall"] is not None else "N/A for this official record"
                    st.caption(f"Reference facts found: {', '.join(result['facts']) or 'none'} · Evidence recall: {recall}")
                    if result.get("summary_metrics"):
                        m = result["summary_metrics"]
                        st.caption(f"Generated summary: {m['input_tokens']} input / {m['output_tokens']} output tokens, {m['latency']:.2f}s; cost included above.")
                    st.info(result["response"] or "No visible response returned.")
                if result["context"]:
                    with st.expander("Context sent to the model"):
                        c = result["context"]
                        st.caption(f"{c['provenance']} · IDs: {', '.join(c['source_ids']) or 'none'} · Estimated: {c['estimated_tokens']} tokens")
                        st.code(c["context"], language="text")


# ------------------------------------------------------------ Demo 2
def _goal_builder_parameters() -> dict:
    if st.session_state.get("goal_id") is None:
        goal = st.text_area("Goal", "Design a REST API for a task management system. Support creating tasks, updating task status, retrieving tasks, and soft deletion. Generate an API specification and a test plan.", key="week2_goal", height=150)
        return {"goal": goal}
    st.caption("A goal is in progress.")
    if st.button("Start a new goal", key="week2_new", width="stretch"):
        st.session_state.goal_id = None
        st.rerun()
    return {}


def _render_goal_builder(settings: ModelSettings, params: dict) -> None:
    st.caption("Persistent state, inspectable context, and one LLM call per workflow step.")
    goal_id = st.session_state.get("goal_id")
    if goal_id is None:
        st.info("Write your goal in 🧪 Lab parameters, then start. The agent's first response appears here.")
        if st.button("Start goal", type="primary", key="week2_create") and can_run(settings, params["goal"]):
            try:
                with st.spinner("Starting the agent…"):
                    state = goal_workflow.start_goal(settings, params["goal"])
                st.session_state.goal_id = state["goal_id"]
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                show_error("Starting the goal", exc)
        return

    try:
        state = load_state(goal_id)
    except FileNotFoundError:
        st.session_state.goal_id = None
        st.rerun()
    index = state["current_step"]
    complete = state["status"] == "complete"
    left, right = st.columns([1, 1.15], gap="large")
    with left:
        st.subheader(state["goal"])
        st.caption(f"Run ID: `{state['goal_id']}` · Status: **{state['status']}**")
        for entry in state["history"]:
            st.caption("You" if entry["role"] == "user" else "🤖 Agent")
            st.markdown(entry["content"])
            st.divider()
        run_step = False
        note = ""
        if complete:
            st.success("You marked this goal complete.")
        else:
            if index >= len(WORKFLOW):
                st.info("The suggested workflow is complete. Keep collaborating until you tell the agent the goal is finished (type “done”).")
            else:
                st.info("Read the latest agent response above, then tell it what to change, clarify or improve. Type “done” to finish.")
            note = st.text_area("Your feedback to the agent", placeholder="For example: Add soft deletion and make task IDs globally unique.", key=f"week2_note_{index}")
            run_step = st.button("Send feedback to agent", type="primary", key="week2_run")
    with right:
        totals = goal_workflow.run_totals(state, settings)
        st.subheader("Run metrics")
        metric_row({"LLM calls": totals["calls"], "Input tokens": totals["input_tokens"],
                    "Output tokens": totals["output_tokens"], "Cost": f"${totals['cost']:.5f}"})
        st.subheader("Step progress")
        for column, (number, (name, _)) in zip(st.columns(len(WORKFLOW)), enumerate(WORKFLOW)):
            marker = "🔵" if number == index and not complete else "🟢" if number < index else "⚪"
            column.markdown(f"{marker}<br><small>{name}</small>", unsafe_allow_html=True)
        if not complete:
            context = goal_workflow.preview_context(state, note)
            with st.expander("Context for the next agent response", expanded=True):
                st.caption(f"Estimated input: {context['estimated_input_tokens']} tokens · Sources: {', '.join(context['provenance'])}")
                st.json(context["context"])
        with st.expander("Feedback remembered by the agent"):
            if state["requirements"]:
                for item in state["requirements"]:
                    st.write(f"• {item['text']}")
            else:
                st.caption("Feedback sent to the agent will be saved here.")
        with st.expander("Inspect persisted state"):
            st.json(state)
        if complete:
            latest = state["history"][-1]["content"] if state["history"] else ""
            st.subheader("Final validation")
            st.json(state["validation_results"][-1] if state["validation_results"] else validate_final_output(state, latest))
    if run_step and (goal_workflow.user_declared_complete(note) or can_run(settings)):
        try:
            with st.spinner(f"Running {goal_workflow.next_operation(state).lower()}…"):
                goal_workflow.run_goal_step(settings, state, note)
            st.rerun()
        except Exception as exc:  # noqa: BLE001
            show_error("Agent step (the workflow was not advanced)", exc)


# ------------------------------------------------------------ Demo 3
def _goal_replay_parameters() -> dict:
    goal = st.text_area("Goal", goal_replay.DEFAULT_GOAL, key="demo3_goal", height=150)
    selected = st.multiselect("Context strategies", list(goal_replay.STRATEGIES),
                              default=list(goal_replay.STRATEGIES), key="demo3_strategies")
    return {"goal": goal, "selected": selected}


def _render_goal_replay(settings: ModelSettings, params: dict) -> None:
    goal, selected = params["goal"], params["selected"]
    st.caption("Replay the same six events in independent sessions and compare context strategies end to end.")
    st.info("Each strategy starts from a new state and cannot see another strategy’s messages or artifacts. "
            "Only context construction changes; the goal, model, events and output limit are fixed.")
    with st.expander("Fixed events supplied to every strategy"):
        st.dataframe([{"Run": n, "Agent operation": WORKFLOW[n - 1][0], "User event": event or "Initial goal"}
                      for n, event in enumerate(goal_replay.CONTROLLED_EVENTS, start=1)],
                     width="stretch", hide_index=True)
    if st.button("Run controlled replay", type="primary", key="demo3_run", disabled=not selected):
        if can_run(settings, goal):
            try:
                with st.spinner(f"Running {len(selected)} independent sessions × {len(WORKFLOW)} calls…"):
                    st.session_state.demo3_results = goal_replay.run_controlled_benchmark(settings, goal.strip(), selected)
            except Exception as exc:  # noqa: BLE001
                show_error("Controlled replay", exc)
    results = st.session_state.get("demo3_results", {})
    if not results:
        return
    rows, chart_rows = goal_replay.comparison_rows(results, settings)
    st.subheader("Final comparison")
    st.dataframe(rows, width="stretch", hide_index=True)
    st.subheader("Context growth by run")
    st.line_chart(chart_rows, x="Run", y="Estimated input tokens", color="Strategy", width="stretch")
    st.subheader("Session inspector")
    for tab, (label, session) in zip(st.tabs(list(results)), results.items()):
        with tab:
            v = session["validation"]
            st.caption(f"Final validation: {'Pass' if v['valid'] else 'Needs review'} · {v['requirements_covered']} of {v['requirements_total']} approved requirements covered")
            for run in session["trace"]:
                with st.expander(f"Run {run['run']} · {run['operation']} — {run['feedback'][:60]}"):
                    st.markdown("**Context sent to the model**")
                    st.json(run["context"]["context"])
                    st.markdown("**Agent response**")
                    st.markdown(run["response"])


if __name__ == "__main__":
    run_standalone(render, "Week 2 · Context Engineering")
