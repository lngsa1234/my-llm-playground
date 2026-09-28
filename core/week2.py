"""The Week 2 multi-run goal builder tab."""

import os
import streamlit as st

from core.context_builder import build_goal_context
from core.demo1 import render_demo1
from core.demo3 import render_demo3
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


def _record_agent_response(state: dict, result: dict, context: dict, operation: str, feedback: str = "") -> dict:
    """Persist one successful agent response and advance the hidden workflow."""
    if feedback.strip():
        state = add_feedback(state, feedback)
    step = state["current_step"] + 1
    state["artifacts"][f"{step}_{operation.lower()}"] = result["text"]
    state["history"].append({"role": "assistant", "kind": operation.lower(), "content": result["text"], "at": utc_now()})
    state["metrics"].append({**result, "step": step, "operation": operation, "estimated_input_tokens": context["estimated_input_tokens"]})
    state["current_step"] = step
    state["status"] = "in_progress"
    state["summary"] = f"Completed {operation}; approved requirements: {[x['text'] for x in state['requirements']]}"
    return state


def _user_declared_complete(message: str) -> bool:
    """Only an explicit user statement, never workflow count, ends a goal."""
    normalized = " ".join(message.lower().replace("'", "").split())
    completion_messages = {
        "done", "finished", "complete", "this is done", "this is finished", "this is complete",
        "the goal is done", "the goal is finished", "the goal is complete", "we are done", "were done",
    }
    return normalized in completion_messages


def _complete_goal(state: dict, user_message: str) -> dict:
    """Record the user's completion declaration and validate the latest agent response."""
    state["history"].append({"role": "user", "kind": "completion", "content": user_message.strip(), "at": utc_now()})
    state["status"] = "complete"
    state["summary"] = "The user declared this goal complete."
    latest_response = next((entry["content"] for entry in reversed(state["history"]) if entry["role"] == "assistant"), "")
    state["validation_results"].append(validate_final_output(state, latest_response))
    return state


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
        render_demo3()


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
            start_goal = st.button("Start goal", type="primary", key="week2_create")
        with settings:
            model, maximum, _, _ = _render_model_settings()
        if start_goal:
            if not goal.strip():
                st.warning("Enter a goal first.")
            elif not os.getenv("OPENAI_API_KEY"):
                st.error("OPENAI_API_KEY is not configured.")
            else:
                state = new_goal_state(goal, "structured")
                operation = WORKFLOW[0][0]
                context = build_goal_context(state, "", token_budget=3500)
                try:
                    with st.spinner("Starting the agent…"):
                        result = execute_goal_call(model, context["context"], operation, maximum)
                    if not validate_response(result["text"])["valid"]:
                        st.error("The agent returned no visible text. The goal was not started.")
                    else:
                        state = _record_agent_response(state, result, context, operation)
                        save_state(state)
                        st.session_state.goal_id = state["goal_id"]
                        st.rerun()
                except Exception as exc:
                    st.error(f"The agent could not start: {exc}")
        return
    try:
        state = load_state(st.session_state.goal_id)
    except FileNotFoundError:
        st.session_state.goal_id = None
        st.rerun()
    index = state["current_step"]
    complete = state["status"] == "complete"
    left, right = st.columns([1, 1.15], gap="large")
    with left:
        st.subheader(state["goal"])
        st.caption(f"Run ID: `{state['goal_id']}` · Strategy: **{state['strategy']}** · Status: **{state['status']}**")
        for entry in state["history"]:
            label = "You" if entry["role"] == "user" else "🤖 Agent"
            st.caption(label)
            st.markdown(entry["content"])
            st.divider()
        if complete:
            st.success("You marked this goal complete.")
        else:
            operation = WORKFLOW[index][0] if index < len(WORKFLOW) else "Continue"
            if index == 0:
                st.info("Start the agent to get its first response to your goal. Then use this box to give feedback on each response.")
                note = st.text_area("Optional instructions for the agent", placeholder="For example: prioritize a simple API design and call out assumptions.", key=f"week2_note_{index}")
                button_label = "Start agent"
            else:
                if index >= len(WORKFLOW):
                    st.info("The suggested workflow is complete. Keep collaborating until you tell the agent that the goal is finished.")
                else:
                    st.info("Read the latest agent response above, then tell it what to change, clarify, or improve.")
                note = st.text_area("Your feedback to the agent", placeholder="For example: Add soft deletion and make task IDs globally unique.", key=f"week2_note_{index}")
                button_label = "Send feedback to agent"
            context = build_goal_context(state, note, token_budget=3500)
            run_step = st.button(button_label, type="primary", key="week2_run")
    with right:
        input_price = float(st.session_state.get("week2_in_price", 0.0))
        output_price = float(st.session_state.get("week2_out_price", 0.0))
        total_in = sum(x["input_tokens"] for x in state["metrics"])
        total_out = sum(x["output_tokens"] for x in state["metrics"])
        st.subheader("Run metrics")
        a, b = st.columns(2)
        a.metric("LLM calls", len(state["metrics"]))
        b.metric("Estimated cost", f"${total_in * input_price / 1_000_000 + total_out * output_price / 1_000_000:.5f}")
        c, d = st.columns(2)
        c.metric("Input tokens", total_in)
        d.metric("Output tokens", total_out)
        st.subheader("Step progress")
        for column, (number, (name, _)) in zip(st.columns(len(WORKFLOW)), enumerate(WORKFLOW)):
            marker = "🔵" if number == index and index < len(WORKFLOW) and not complete else "🟢" if number < index else "⚪"
            column.markdown(f"{marker}<br><small>{name}</small>", unsafe_allow_html=True)
        model = str(st.session_state.get("week2_model", "gpt-5.4-mini"))
        maximum = int(st.session_state.get("week2_tokens", 1200))
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
    if not complete and run_step:
        if _user_declared_complete(note):
            state = _complete_goal(state, note)
            save_state(state)
            st.rerun()
        elif not os.getenv("OPENAI_API_KEY"):
            st.error("OPENAI_API_KEY is not configured.")
        else:
            try:
                with st.spinner(f"Running {operation.lower()}…"):
                    result = execute_goal_call(model, context["context"], operation, maximum)
                if not validate_response(result["text"])["valid"]:
                    st.error("Step was not saved because the model returned no visible text.")
                else:
                    state = _record_agent_response(state, result, context, operation, note)
                    save_state(state)
                    st.rerun()
            except Exception as exc:
                st.error(f"API call failed; the workflow was not advanced: {exc}")


def render_demo2() -> None:
    """Render the persistent, six-call Demo 2 goal-builder workflow."""
    _render_demo2_builder()
