"""The Week 2 multi-run goal builder tab."""

import os
import streamlit as st

from core.context_builder import build_goal_context
from core.demo1 import render_demo1
from core.evaluator import validate_final_output, validate_response
from core.llm_client import execute_goal_call
from core.state_manager import WORKFLOW, add_feedback, load_state, new_goal_state, save_state, utc_now


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
        return
    try:
        state = load_state(st.session_state.goal_id)
    except FileNotFoundError:
        st.session_state.goal_id = None
        st.rerun()
    index = state["current_step"]
    complete = index >= len(WORKFLOW)
    left, right = st.columns([1, 1.15], gap="large")
    with left:
        st.subheader(state["goal"])
        st.caption(f"Run ID: `{state['goal_id']}` · Strategy: **{state['strategy']}** · Status: **{state['status']}**")
        st.subheader("Your conversation")
        progress_label = "The goal is complete" if complete else f"The agent is preparing response {index + 1} of {len(WORKFLOW)}"
        st.progress(index / len(WORKFLOW), text=f"Goal progress — {index} of {len(WORKFLOW)} responses complete")
        st.caption(progress_label)
        for entry in state["history"]:
            with st.chat_message(entry["role"]):
                if entry["role"] == "assistant":
                    st.caption(f"Agent · {entry.get('kind', 'response').title()}")
                st.markdown(entry["content"])
        if complete:
            st.success("All six workflow steps are complete.")
        else:
            operation, description = WORKFLOW[index]
            if index == 0:
                st.info("Start the agent to get its first response to your goal. Then use this box to give feedback on each response.")
                note = st.text_area("Optional instructions for the agent", placeholder="For example: prioritize a simple API design and call out assumptions.", key=f"week2_note_{index}")
                button_label = "Start agent"
            else:
                st.info("Read the latest agent response above, then tell it what to change, clarify, or improve.")
                note = st.text_area("Your feedback to the agent", placeholder="For example: Add soft deletion and make task IDs globally unique.", key=f"week2_note_{index}")
                button_label = "Send feedback to agent"
            context = build_goal_context(state, note, token_budget=3500)
            run_step = st.button(button_label, type="primary", key="week2_run")
    with right:
        st.subheader("Model settings")
        model, maximum, input_price, output_price = _render_model_settings()
        st.subheader("Artifacts")
        if state["artifacts"]:
            tabs = st.tabs(list(state["artifacts"].keys()))
            for tab, (_, content) in zip(tabs, state["artifacts"].items()):
                with tab:
                    st.markdown(content)
        else:
            st.caption("Generated artifacts will be collected here as the conversation progresses.")
        if not complete:
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
            validation = state["validation_results"][-1] if state["validation_results"] else validate_final_output(state, latest)
            st.subheader("Final validation")
            st.json(validation)
        if state["metrics"]:
            total_in = sum(x["input_tokens"] for x in state["metrics"])
            total_out = sum(x["output_tokens"] for x in state["metrics"])
            st.subheader("Run metrics")
            a, b = st.columns(2)
            a.metric("LLM calls", len(state["metrics"]))
            b.metric("Estimated cost", f"${total_in * input_price / 1_000_000 + total_out * output_price / 1_000_000:.5f}")
            c, d = st.columns(2)
            c.metric("Input tokens", total_in)
            d.metric("Output tokens", total_out)
    if not complete and run_step:
        if not os.getenv("OPENAI_API_KEY"):
            st.error("OPENAI_API_KEY is not configured.")
        else:
            try:
                with st.spinner(f"Running {operation.lower()}…"):
                    result = execute_goal_call(model, context["context"], operation, maximum)
                if not validate_response(result["text"])["valid"]:
                    st.error("Step was not saved because the model returned no visible text.")
                else:
                    artifact = f"{index + 1}_{operation.lower()}"
                    if note.strip():
                        state = add_feedback(state, note)
                    state["artifacts"][artifact] = result["text"]
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


def render_demo2() -> None:
    """Render the persistent, six-call Demo 2 goal-builder workflow."""
    _render_demo2_builder()
