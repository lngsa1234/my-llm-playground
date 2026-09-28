"""The Week 2 multi-run goal builder tab."""

import os
import streamlit as st

from core.context_builder import build_goal_context
from core.demo1 import render_demo1
from core.evaluator import validate_final_output, validate_response
from core.llm_client import execute_goal_call
from core.state_manager import WORKFLOW, add_feedback, list_states, load_state, new_goal_state, save_state, utc_now


def _render_model_settings() -> tuple[str, int, float, float]:
    """Render shared LLM settings in the right-hand control column."""
    model = st.text_input("Model", "gpt-5.4-mini", key="week2_model")
    maximum = st.number_input("Max output tokens", 200, 4000, 1200, 100, key="week2_tokens")
    input_price = st.number_input("Input $ / 1M", 0.0, 0.75, format="%.4f", key="week2_in_price")
    output_price = st.number_input("Output $ / 1M", 0.0, 4.50, format="%.4f", key="week2_out_price")
    return model, int(maximum), input_price, output_price


def _render_context_approach() -> None:
    st.info(
        "**Context approach: hybrid structured context.** For every agent call, the app rebuilds context "
        "from the goal and approved requirements (durable state), a compact summary plus recent messages "
        "(memory), and relevant earlier artifacts (working documents). This combines Demo 1’s **Summary + "
        "recent** idea with application-specific state, so the agent receives what matters without sending "
        "the entire conversation every time."
    )


def render_week2() -> None:
    """Render the three Week 2 lab demos."""
    st.header("Week 2 · Context Engineering")
    demo1, demo2, demo3 = st.tabs(
        [
            "Demo 1 · Benchmark",
            "Demo 2 · Multi-Run Builder",
            "Demo 3 · Context Builder Eval",
        ]
    )
    with demo1:
        render_demo1()
    with demo2:
        render_demo2()
    with demo3:
        st.subheader("Context Builder Evaluation")
        st.info("Coming soon!")


def _render_demo2_builder() -> None:
    st.header("Demo 2 · Multi-Run Goal Builder")
    st.caption("Persistent state, inspectable context, and one LLM call per workflow step.")
    _render_context_approach()
    if "goal_id" not in st.session_state:
        st.session_state.goal_id = None
    saved = list_states()
    labels = {f"{x['goal_id']} · {x['goal'][:38]}": x["goal_id"] for x in saved}
    if st.session_state.goal_id is None:
        st.subheader("Set your goal")
        start, settings = st.columns([2, 1])
        with start:
            goal = st.text_area("Goal", "Design a REST API for a task management system. Support creating tasks, updating task status, retrieving tasks, and soft deletion. Generate an API specification and a test plan.", key="week2_goal", height=115)
            if st.button("Start goal", type="primary", key="week2_create"):
                if goal.strip():
                    state = new_goal_state(goal, "structured")
                    save_state(state)
                    st.session_state.goal_id = state["goal_id"]
                    st.rerun()
                else:
                    st.warning("Enter a goal first.")
        with settings:
            _render_model_settings()
        if labels:
            st.divider()
            st.subheader("Resume a saved run")
            selected = st.selectbox("Saved Week 2 runs", ["Choose a run"] + list(labels), key="week2_resume")
            if st.button("Load selected run", disabled=selected == "Choose a run", key="week2_load"):
                st.session_state.goal_id = labels[selected]
                st.rerun()
        return
    try:
        state = load_state(st.session_state.goal_id)
    except FileNotFoundError:
        st.session_state.goal_id = None
        st.rerun()
    index = state["current_step"]
    complete = index >= len(WORKFLOW)
    st.subheader(state["goal"])
    st.caption(f"Run ID: `{state['goal_id']}` · Strategy: **{state['strategy']}** · Status: **{state['status']}**")
    control, settings = st.columns([2, 1])
    with control:
        selected = st.selectbox("Resume a saved Week 2 run", ["Choose a run"] + list(labels), key="week2_resume")
        if st.button("Load selected run", disabled=selected == "Choose a run", key="week2_load"):
            st.session_state.goal_id = labels[selected]
            st.rerun()
    with settings:
        model, maximum, input_price, output_price = _render_model_settings()
    progress = index / len(WORKFLOW)
    progress_label = "Complete" if complete else f"Next: Step {index + 1} · {WORKFLOW[index][0]}"
    progress_left, progress_right = st.columns([5, 1])
    with progress_left:
        st.progress(progress, text=f"Workflow progress — {index} of {len(WORKFLOW)} steps complete")
    with progress_right:
        st.metric("Current status", progress_label)
    for col, (number, (name, _)) in zip(st.columns(6), enumerate(WORKFLOW)):
        col.caption(f"{'✓' if number < index else '○'} {name}")
    left, right = st.columns([1, 1.15], gap="large")
    with left:
        st.subheader("Approved changes")
        feedback = st.text_area("Feedback or changed requirement", placeholder="Task IDs must be globally unique.", key="week2_feedback")
        if st.button("Save feedback", key="week2_save_feedback"):
            if feedback.strip():
                save_state(add_feedback(state, feedback))
                st.rerun()
            else:
                st.warning("Enter feedback to save.")
        for item in state["requirements"]:
            st.write(f"• {item['text']}")
        with st.expander("Inspect persisted state"):
            st.json(state)
    with right:
        if complete:
            st.success("All six workflow steps are complete.")
            latest = state["history"][-1]["content"] if state["history"] else ""
            validation = state["validation_results"][-1] if state["validation_results"] else validate_final_output(state, latest)
            st.json(validation)
        else:
            operation, description = WORKFLOW[index]
            st.subheader(f"Step {index + 1}: {operation}")
            st.write(description)
            st.info("Tell the agent what to prioritize, clarify, or change. Use **Approved changes** for requirements that must persist through every future step.")
            note = st.text_area("Message to your agent", placeholder="For this step, prioritize a simple API design and call out any assumptions.", key=f"week2_note_{index}")
            context = build_goal_context(state, note, token_budget=3500)
            with st.expander("Inspect constructed context", expanded=True):
                st.caption(f"Estimated input: {context['estimated_input_tokens']} tokens · Sources: {', '.join(context['provenance'])}")
                st.json(context["context"])
            if st.button(f"Send to agent: {operation}", type="primary", key="week2_run"):
                if not os.getenv("OPENAI_API_KEY"):
                    st.error("OPENAI_API_KEY is not configured.")
                else:
                    try:
                        with st.spinner(f"Running {operation.lower()}…"):
                            result = execute_goal_call(model, context["context"], operation, int(maximum))
                        if not validate_response(result["text"])["valid"]:
                            st.error("Step was not saved because the model returned no visible text.")
                        else:
                            artifact = f"{index + 1}_{operation.lower()}"
                            state["artifacts"][artifact] = result["text"]
                            if note.strip():
                                state["history"].append({"role": "user", "kind": "message", "content": note.strip(), "at": utc_now()})
                            state["history"].append({"role": "assistant", "kind": operation.lower(), "content": result["text"], "at": utc_now()})
                            state["metrics"].append({**result, "step": index + 1, "operation": operation, "estimated_input_tokens": context["estimated_input_tokens"]})
                            state["current_step"] += 1
                            state["status"] = "complete" if state["current_step"] == len(WORKFLOW) else "in_progress"
                            state["summary"] = f"Completed {operation}; approved requirements: {[x['text'] for x in state['requirements']]}"
                            if state["status"] == "complete":
                                state["validation_results"].append(validate_final_output(state, result["text"]))
                            save_state(state)
                            st.rerun()
                    except Exception as exc:
                        st.error(f"API call failed; the workflow was not advanced: {exc}")
    st.subheader("Artifacts and cumulative metrics")
    if state["artifacts"]:
        tabs = st.tabs(list(state["artifacts"].keys()))
        for tab, (_, content) in zip(tabs, state["artifacts"].items()):
            with tab:
                st.markdown(content)
    if state["metrics"]:
        total_in = sum(x["input_tokens"] for x in state["metrics"])
        total_out = sum(x["output_tokens"] for x in state["metrics"])
        a, b, c, d = st.columns(4)
        a.metric("LLM calls", len(state["metrics"]))
        b.metric("Input tokens", total_in)
        c.metric("Output tokens", total_out)
        d.metric("Estimated cost", f"${total_in * input_price / 1_000_000 + total_out * output_price / 1_000_000:.5f}")


def render_demo2() -> None:
    """Render the persistent, six-call Demo 2 goal-builder workflow."""
    _render_demo2_builder()
