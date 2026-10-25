"""Week 6 page: evaluate an agent, then catch a regression before it ships.

Run alone:   streamlit run labs/week6_agent_eval/page.py
In the site: streamlit run app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Lets this page run on its own (streamlit run labs/<lab>/page.py) as well as inside app.py.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from labs.shared.settings import ModelSettings
from labs.week6_agent_eval import evals
from labs.shared.ui import mini_muse_part, can_run, lab_parameters, metric_row, model_settings, page_layout, show_error, run_standalone

HOW_IT_WORKS = """
You evaluate **Muse**, a small personal-assistant agent that checks weather, reads and books calendar events, drafts emails and does tip math. **v1** is in production; **v2** is a “faster, friendlier” update. Is v2 safe to ship?

0. **Explore the agent** — try requests by hand and look at what each version does. No grading: this is the “it looks good when I try it” baseline the rest of the lab improves on.
1. **Golden dataset** — 12 hand-written cases with the expected behavior written down first: answer checks, the right tool path, forbidden tools and expected side effects.
2. **Task success** — grade the *outcome*: is the answer right, and is the world in the right state afterwards?
3. **Tool evaluation** — grade the *path*: right tools, right order, right arguments, and no forbidden calls.
4. **LLM-as-a-judge** — a rubric scores faithfulness, helpfulness, safety and tone, then the judge is checked against human labels.
5. **Regression** — run everything on v1 and v2, diff case by case, and apply release gates.

Muse is rule-based, so the agent itself makes no API calls. Only the optional **LLM judge** uses the model in ⚙️ Model settings. The same lab runs from the command line: `python3 labs/week6_agent_eval/run_all.py`.
"""

STEPS = ["0 · Explore the agent (no grading)", "1 · Golden dataset", "2 · Task success", "3 · Tool evaluation",
         "4 · LLM-as-a-judge", "5 · Regression"]
JUDGES = ["Heuristic (offline, free)", "LLM judge (uses Model settings)"]


def render() -> None:
    main, panel = page_layout("Week 6 · Agent Evaluation")
    if mini_muse_part(main, panel, 6,
                      caption="Goal: decide whether Muse v2 is safe to ship, using evidence instead of a demo, and catch what the update broke before users do.",
                      how_it_works=HOW_IT_WORKS):
        return
    settings = model_settings(panel)
    with lab_parameters(panel):
        step = st.radio("Step", STEPS, key="week6_step")
        st.divider()
        params = {"step": step}
        if step in STEPS[2:5]:
            params["version"] = st.radio("Agent version", evals.VERSIONS, format_func=evals.VERSION_LABELS.get, key="week6_version")
        if step in STEPS[4:]:
            params["judge"] = st.radio("Judge", JUDGES, key="week6_judge")
            if params["judge"] == JUDGES[1]:
                st.caption("One model call per case; the regression step judges both versions.")
        if step == STEPS[5]:
            st.caption("Baseline: v1 · Candidate: v2")
            params["gates"] = {
                "max_safety_violations": int(st.number_input("Max safety violations", 0, 10, 0, key="week6_gate_safety")),
                "max_new_failures": int(st.number_input("Max new failures (pass → fail)", 0, 50, 0, key="week6_gate_new")),
                "max_metric_drop": st.slider("Max drop in any pass rate", 0.0, 0.5, 0.05, 0.01, format="%.2f", key="week6_gate_drop"),
            }
    with main:
        st.subheader(step)
        if step == STEPS[0]:
            _render_explore()
        elif step == STEPS[1]:
            _render_dataset()
        elif step == STEPS[2]:
            _render_task_success(params["version"])
        elif step == STEPS[3]:
            _render_tool_eval(params["version"])
        elif step == STEPS[4]:
            _render_judge(settings, params["version"], params["judge"])
        else:
            _render_regression(settings, params["judge"], params["gates"])


def _render_explore() -> None:
    st.caption("Try requests by hand and compare the two versions. Nothing is graded here: you judge by eye. "
               "Pick a golden-dataset request to see how the same request is written down and graded automatically.")
    source = st.radio("Request", ["From the golden dataset", "Type your own"], horizontal=True, key="week6_explore_source")
    case = None
    if source == "From the golden dataset":
        cases = evals.load_cases()
        case = st.selectbox("Golden-dataset case", cases, key="week6_explore_case",
                            format_func=lambda c: f"{c['id']} · {c['input']}")
        query = case["input"]
    else:
        query = st.text_input("Your request", "Schedule lunch on 2026-10-28 at 12:00", key="week6_explore_custom")
    if not query.strip():
        return

    st.markdown("#### What each version does")
    for column, version in zip(st.columns(2), evals.VERSIONS):
        with column:
            trace = evals.run_agent(query, version)
            st.markdown(f"**{evals.VERSION_LABELS[version]}**")
            st.info(trace["answer"])
            st.caption(f"Tools called: {' → '.join(c['tool'] for c in trace['tool_calls']) or '(none)'} · "
                       f"Events booked: {len(trace['final_state']['events_created'])} · "
                       f"Emails sent: {len(trace['final_state']['emails_sent'])}")
            with st.popover("Full trace"):
                st.json(trace)

    if case is None:
        st.info("This request isn't in the golden dataset, so there is no written-down expected behavior to grade it against. "
                "To grade it on every run, add it to `labs/week6_agent_eval/data/golden.jsonl` with its expected behavior.")
        return

    exp = case["expected"]
    st.markdown("#### What the golden dataset says should happen")
    st.caption(f"Written down before looking at any output. Why this case exists: {case.get('notes', '—')}")
    rules = []
    if exp["must_contain"]:
        rules.append(f"- Answer **must mention**: {', '.join(repr(x) for x in exp['must_contain'])}")
    if exp["must_not_contain"]:
        rules.append(f"- Answer **must not say**: {', '.join(repr(x) for x in exp['must_not_contain'])}")
    rules.append(f"- Tools to call, in order: {' → '.join(exp['expected_tools']) or '(none)'}")
    if exp["forbidden_tools"]:
        rules.append(f"- Tools that must **never** be called here: {', '.join(exp['forbidden_tools'])}")
    rules.append(f"- Side effects afterwards: {exp['expected_state']['events_created']} event(s) booked, "
                 f"{exp['expected_state']['emails_sent']} email(s) sent")
    st.markdown("\n".join(rules))

    st.markdown("#### Graded automatically")
    for column, version in zip(st.columns(2), evals.VERSIONS):
        with column:
            graded = evals.grade_case(case, version)
            st.markdown(f"**{version}**")
            task_icon = "✅" if graded["task_passed"] else "❌"
            tool_icon = "✅" if graded["tools_passed"] else "❌"
            st.markdown(f"{task_icon} **Task success** (step 2)" +
                        ("" if graded["task_passed"] else "  \n" + "  \n".join(f"· failed: {f}" for f in graded["task_failed"])))
            st.markdown(f"{tool_icon} **Tool use** (step 3)" +
                        ("" if graded["tools_passed"] else "  \n" + "  \n".join(f"· {f}" for f in graded["tool_problems"])))
    st.caption("Steps 1–5 do this for all 12 cases at once, every time the agent changes.")


def _render_dataset() -> None:
    st.caption("A golden dataset is a small set of realistic inputs with the expected behavior written down *before* you look at outputs. Every later step grades against it.")
    cases = evals.load_cases()
    report = evals.dataset_report(cases)
    metric_row({"Cases": len(cases), "Categories": len(report["categories"]),
                "Side-effect cases": report["side_effect_cases"], "Hard cases": f"{report['hard_share']:.0%}"})
    st.markdown("**Coverage by category**")
    st.bar_chart({k: [v] for k, v in sorted(report["categories"].items())}, horizontal=True, stack=False)
    st.markdown("**Linter**")
    if report["problems"]:
        for problem in report["problems"]:
            st.error(problem)
    else:
        st.success("No schema problems.")
    for warning in report["warnings"]:
        st.warning(warning)
    thin = [k for k, v in report["categories"].items() if v < 2]
    if thin:
        st.warning(f"Thin categories (fewer than 2 cases): {', '.join(thin)}")
    st.markdown("**Cases**")
    st.dataframe([{"Case": c["id"], "Category": c["category"], "Difficulty": c["difficulty"], "Input": c["input"],
                   "Expected tools": " → ".join(c["expected"]["expected_tools"]) or "(none)",
                   "Forbidden tools": ", ".join(c["expected"]["forbidden_tools"]), "Why it exists": c.get("notes", "")}
                  for c in cases], width="stretch", hide_index=True)
    st.caption("Edit `labs/week6_agent_eval/data/golden.jsonl` to add cases; this page reads it directly.")


def _render_task_success(version: str) -> None:
    st.caption("Grade the outcome only: the final answer and the end state of the world (events booked, emails sent).")
    rows, rate = evals.task_results(version)
    metric_row({"Task success": f"{rate:.0%}", "Passed": sum(r["Result"] == "PASS" for r in rows), "Failed": sum(r["Result"] == "FAIL" for r in rows)})
    st.dataframe(rows, width="stretch", hide_index=True)
    if version == "v2":
        st.info("Look at **sch-01**: it passes here. Switch to **3 · Tool evaluation** to see why it shouldn't.")


def _render_tool_eval(version: str) -> None:
    st.caption("Grade the path, not just the destination: an agent can reach a right answer the wrong way.")
    rows, s = evals.tool_results(version)
    metric_row({"Tool-use pass rate": f"{s['pass_rate']:.0%}", "Precision": f"{s['precision']:.0%}", "Recall": f"{s['recall']:.0%}",
                "Correct order": f"{s['order']:.0%}", "Safety violations": s["safety_violations"]})
    st.dataframe(rows, width="stretch", hide_index=True)
    if s["safety_violations"]:
        st.error(f"{s['safety_violations']} forbidden tool call(s). Safety violations should always be zero.")


def _judge_function(settings: ModelSettings, judge_name: str, usage: dict):
    return evals.heuristic_judge if judge_name == JUDGES[0] else evals.llm_judge(settings, usage)


def _render_judge(settings: ModelSettings, version: str, judge_name: str) -> None:
    st.caption("A rubric grades what string checks can't, and the judge is compared with human labels before it's trusted.")
    with st.expander("Rubric and judge prompt"):
        st.dataframe([{"Criterion": k, "What it means": v} for k, v in evals.RUBRIC.items()], width="stretch", hide_index=True)
        st.code(evals.judge_prompt_example(version), language="text")
    key = ("judge", version, judge_name, settings.model)
    if judge_name == JUDGES[0]:
        st.session_state.week6_judge_result = {"key": key, "result": evals.judge_results(version, evals.heuristic_judge), "usage": {}}
    elif st.button(f"Run LLM judge on {version} ({len(evals.load_cases())} calls)", type="primary", key="week6_judge_run") and can_run(settings):
        usage: dict = {}
        try:
            with st.spinner("Judging each case…"):
                result = evals.judge_results(version, evals.llm_judge(settings, usage))
            st.session_state.week6_judge_result = {"key": key, "result": result, "usage": usage}
        except Exception as exc:  # noqa: BLE001
            show_error("LLM judge", exc)
    stored = st.session_state.get("week6_judge_result")
    if not stored or stored["key"] != key:
        st.info("Run the LLM judge to score this version.")
        return
    result, usage = stored["result"], stored["usage"]
    agreement = result["agreement"]
    metric_row({"Judge pass rate": f"{result['pass_rate']:.0%}",
                **{k.title(): f"{v:.1f}" for k, v in result["averages"].items()},
                "Judge–human agreement": "—" if agreement is None else f"{agreement:.0%}"})
    if usage:
        st.caption(f"{usage['calls']} judge calls · {usage['input_tokens']} input / {usage['output_tokens']} output tokens · "
                   f"${settings.cost(usage['input_tokens'], usage['output_tokens']):.4f}")
    if agreement is not None and agreement < 0.85:
        st.warning(f"Agreement with humans is {agreement:.0%} on {result['labeled']} labeled cases. Don't trust a judge below about 85%: look at the ⚠ rows.")
    st.dataframe(result["rows"], width="stretch", hide_index=True)


def _render_regression(settings: ModelSettings, judge_name: str, gates: dict) -> None:
    st.caption("Run every evaluation on the baseline and the candidate, diff case by case, and apply release gates.")
    key = ("regression", judge_name, settings.model, tuple(sorted(gates.items())))
    if judge_name == JUDGES[0]:
        st.session_state.week6_regression_result = {"key": key, "result": evals.regression("v1", "v2", evals.heuristic_judge, gates), "usage": {}}
    elif st.button(f"Run regression with the LLM judge ({2 * len(evals.load_cases())} calls)", type="primary", key="week6_regression_run") and can_run(settings):
        usage: dict = {}
        try:
            with st.spinner("Evaluating v1 and v2…"):
                result = evals.regression("v1", "v2", evals.llm_judge(settings, usage), gates)
            st.session_state.week6_regression_result = {"key": key, "result": result, "usage": usage}
        except Exception as exc:  # noqa: BLE001
            show_error("Regression", exc)
    stored = st.session_state.get("week6_regression_result")
    if not stored or stored["key"] != key:
        st.info("Run the regression with the LLM judge to compare v1 and v2.")
        return
    result = stored["result"]
    base, cand = result["base"]["metrics"], result["cand"]["metrics"]
    if result["ship"]:
        st.success("Verdict: SHIP IT ✅ — every release gate passed.")
    else:
        st.error("Verdict: BLOCK RELEASE ❌ — at least one release gate failed.")
    st.dataframe([{"Metric": f"{d.title()} pass rate", "Baseline v1": f"{base[d]:.0%}", "Candidate v2": f"{cand[d]:.0%}",
                   "Change": f"{cand[d] - base[d]:+.0%}"} for d in evals.DIMENSIONS]
                 + [{"Metric": "Safety violations", "Baseline v1": str(base["safety_violations"]),
                     "Candidate v2": str(cand["safety_violations"]),
                     "Change": f"{cand['safety_violations'] - base['safety_violations']:+d}"}], width="stretch", hide_index=True)
    st.markdown("**Release gates**")
    for gate, ok in result["gates"].items():
        st.markdown(f"{'✅' if ok else '❌'} {gate}")
    st.markdown(f"**New failures ({len(result['new_failures'])})** — cases that passed on v1 and fail on v2")
    if result["new_failures"]:
        st.dataframe(result["new_failures"], width="stretch", hide_index=True)
    if result["fixed"]:
        st.markdown(f"**Fixed ({len(result['fixed'])})**")
        st.dataframe(result["fixed"], width="stretch", hide_index=True)
    st.download_button("Download regression report (Markdown)", evals.regression_report(result),
                       file_name="regression_report.md", mime="text/markdown", key="week6_report")


if __name__ == "__main__":
    run_standalone(render, "Week 6 · Agent Evaluation")
