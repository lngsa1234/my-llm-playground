"""Week 5 page: a stateful workflow agent with a bounded control loop.

Run alone:   streamlit run labs/week5_agent_workflow/page.py
In the site: streamlit run app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Lets this page run on its own (streamlit run labs/<lab>/page.py) as well as inside app.py.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import time

import streamlit as st

from labs.shared.ui import (can_run, example_text_area, lab_parameters, metric_row, mini_muse_part, model_settings, page_layout,
                            run_standalone, show_error, usage_metrics)
from labs.week5_agent_workflow import workflow_agent as wf

HOW_IT_WORKS = """
The agent moves a writing request through an explicit workflow, one stage per step:

1. **State**: everything the agent knows (stage, step count, repair count, requirements, draft, QA result) lives in one `AgentState` object. Open **Final state** to see it.
2. **Actions** do the work of a stage and report what they observed. Triage, requirements and planning use structured output. Drafting writes the text. QA runs a **code check first** (word limit, required phrases), and only calls the model if the code check passes.
3. The **router** reads the updated state and picks the next stage, with a reason. The default router is plain code. Switch to the **LLM router** to let the model choose (the lab's Experiment B).
4. The **workflow** checks every decision. An illegal jump, such as triage → complete, ends the run as failed.
5. **Boundaries** stop the loop cleanly: max steps, the repair budget, an action error, or an illegal transition. Every run ends in *complete* or *failed*, always with a reason.

Code: `labs/week5_agent_workflow/workflow_agent.py`. The TypeScript version of this lab is in the knowledge base.
"""


def _graph(state: wf.AgentState | None) -> str:
    visited = {row["stage"] for row in state.trace} if state else set()
    taken = {(row["stage"], row["next"]) for row in state.trace} if state else set()
    final = state.stage if state else None
    lines = ['digraph { rankdir=LR; bgcolor="transparent"; node [shape=box, style="rounded,filled", fontname="Helvetica", '
             'fontsize=11, fillcolor="#ffffff", color="#999999"]; edge [color="#bbbbbb", fontname="Helvetica", fontsize=9];']
    for stage in wf.STAGES:
        fill = ("#d9f2df" if stage == "complete" else "#fbe0de") if stage == final else "#e6eefc" if stage in visited else "#ffffff"
        lines.append(f'{stage} [label="{stage.upper()}", fillcolor="{fill}"];')
    for src, dsts in wf.TRANSITIONS.items():
        for dst in dsts:
            style = 'color="#3b6fd8", penwidth=2' if (src, dst) in taken else ""
            label = ' label="repair"' if (src, dst) == ("qa", "drafting") else ""
            lines.append(f"{src} -> {dst} [{style}{label}];")
    return "\n".join(lines) + "}"


def render() -> None:
    main, panel = page_layout("Week 5 · Agent Workflow")
    if mini_muse_part(main, panel, 5,
                      caption="Move a request through an explicit workflow: state, router, repair budget and a bounded loop.",
                      how_it_works=HOW_IT_WORKS):
        return
    settings = model_settings(panel)
    with lab_parameters(panel):
        max_steps = st.slider("Max steps", 2, 20, 12, key="week5_max_steps", help="Boundary 1: the loop stops here.")
        max_repairs = st.slider("Repair budget", 0, 4, 2, key="week5_max_repairs",
                                help="How many times a failed QA may send the draft back for a fix.")
        router_kind = st.radio("Router", ["Code (rules)", "LLM decides"], key="week5_router",
                               help="Experiment B: let the model pick the next stage. The workflow still validates it.")
        force_fail = st.checkbox("Make QA always fail", key="week5_force_fail",
                                 help="Experiment C: watch the repair budget end the run.")

    with main:
        request = example_text_area("Request", wf.EXAMPLES, "week5", height=90)

        if st.button("Run the agent", type="primary", key="week5_run") and can_run(settings, request):
            model = wf.Model(settings)
            state = wf.AgentState(request, max_steps=max_steps, max_repairs=max_repairs)
            router = wf.llm_route(model) if router_kind == "LLM decides" else wf.route
            live = st.empty()
            started = time.perf_counter()
            try:
                wf.run_agent(state, model, router, {"force_qa_fail": force_fail},
                             on_step=lambda _row: live.dataframe(_rows(state), width="stretch", hide_index=True))
            except Exception as exc:  # noqa: BLE001
                show_error("Agent run", exc)
            live.empty()
            st.session_state.week5_result = {"state": state, "model": model, "seconds": time.perf_counter() - started}

        result = st.session_state.get("week5_result")
        state = result["state"] if result else None
        if state:
            if state.status == "complete":
                st.success(f"COMPLETE after {state.step_count} steps and {state.repair_count} repair{'s' * (state.repair_count != 1)}.")
            else:
                st.error(f"FAILED at step {state.step_count}: {state.failure_reason}")
            metric_row({"Steps": f"{state.step_count} / {state.max_steps}",
                        "Repairs": f"{state.repair_count} / {state.max_repairs}",
                        "Model calls": result["model"].calls})
        st.graphviz_chart(_graph(state))
        if state:
            st.markdown("**Trace**: one row per step, with what the action observed and why the router moved on")
            st.dataframe(_rows(state), width="stretch", hide_index=True)
            left, right = st.columns(2, gap="large")
            with left:
                st.markdown("**Draft**")
                st.info(state.draft or "(no draft)")
            with right:
                st.markdown("**Last QA**")
                if state.qa:
                    st.write(f"{'✅ Passed' if state.qa['passed'] else '❌ Failed'} · checked by **{state.qa['checked_by']}**")
                    st.caption(state.qa["feedback"])
                if state.requirements:
                    st.markdown("**Requirements**")
                    st.json(state.requirements, expanded=False)
            m = result["model"]
            usage_metrics(m.input_tokens, m.output_tokens, result["seconds"], m.cost())
            with st.expander("Final state"):
                st.json(state.snapshot())


def _rows(state: wf.AgentState) -> list[dict]:
    return [{"Step": r["step"], "Stage": r["stage"], "Observed": r["observed"], "Next": r["next"],
             "Reason": r["reason"], "Tokens": r["tokens"], "s": r["seconds"]} for r in state.trace]


if __name__ == "__main__":
    run_standalone(render, "Week 5 · Agent Workflow")
