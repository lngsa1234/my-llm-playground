"""Week 4 page: a tool-calling weather assistant."""

from __future__ import annotations

import streamlit as st

from core.week4 import weather
from ui.components import can_run, lab_parameters, metric_row, model_settings, page_header, page_layout, show_error

HOW_IT_WORKS = """
1. The model receives your prompt plus two **tool schemas**: `get_weather` (current conditions) and `get_weekend_forecast` (upcoming Saturday and Sunday).
2. If it decides it needs data, it returns a **tool call**. The app — not the model — runs the tool against the live Open-Meteo API.
3. The tool result goes back to the model, which can call more tools or answer. **Max tool-call rounds** caps this loop.
4. **Run without tools** shows the same model with no weather access, for comparison.
5. The **benchmark** checks tool selection and location arguments on 11 prompts, including one that needs no tool and one invalid place.
"""


def render() -> None:
    page_header("Week 4 · Weather Assistant",
                "Ask about current conditions or which weekend day is best, and inspect every tool call.",
                HOW_IT_WORKS)
    main, panel = page_layout()
    settings = model_settings(panel, prices=False)
    with lab_parameters(panel):
        max_rounds = int(st.slider("Max tool-call rounds", 1, 10, 5, key="week4_max_rounds"))
        st.caption("How many times the model may request tools before the run stops.")

    with main:
        # Streamlit keeps keyed widget values between reruns. Upgrade only the old stock
        # prompt so a learner's own in-progress question is never overwritten.
        if st.session_state.get("week4_prompt") == weather.LEGACY_DEFAULT_PROMPT:
            st.session_state.week4_prompt = weather.DEFAULT_PROMPT
        prompt = st.text_area("Prompt", weather.DEFAULT_PROMPT, key="week4_prompt", height=90)
        with_tools, without_tools = st.columns(2)
        run_with = with_tools.button("Run with tools", type="primary", width="stretch", key="week4_run_tools")
        run_without = without_tools.button("Run without tools", width="stretch", key="week4_run_plain")
        if (run_with or run_without) and can_run(settings, prompt):
            try:
                message = "Model deciding; runtime executing any requested tools…" if run_with else "Running model without weather tools…"
                with st.spinner(message):
                    st.session_state.week4_result = weather.run_direct_agent(
                        prompt, settings.model, use_tools=run_with, max_tool_rounds=max_rounds,
                        max_output_tokens=settings.max_output_tokens)
            except Exception as exc:  # noqa: BLE001
                show_error("Agent request", exc)

        result = st.session_state.get("week4_result")
        if result:
            st.subheader("Answer")
            st.caption(result.get("mode", "With tools"))
            st.write(result["answer"])
            metric_row({"Tool calls": len(result["trace"]), "Latency": f"{result['latency']:.2f}s"})
            with st.expander("Runtime trace", expanded=True):
                if result["trace"]:
                    st.json(result["trace"])
                else:
                    st.info("No tool was requested: the expected outcome for conceptual questions.")
        with st.expander("Tool schemas supplied to the model"):
            st.json([weather.WEATHER_TOOL, weather.WEEKEND_FORECAST_TOOL])

        st.divider()
        st.subheader("Benchmark")
        st.caption(f"Run {len(weather.LIVE_BENCHMARKS)} prompts to measure tool selection and location arguments. "
                   "This calls the OpenAI API and the weather service.")
        if st.button("Run live benchmark", width="stretch", key="week4_benchmark_run") and can_run(settings):
            try:
                with st.spinner(f"Running {len(weather.LIVE_BENCHMARKS)} benchmark prompts…"):
                    rows, details = weather.run_live_benchmark(settings.model, max_tool_rounds=max_rounds,
                                                               max_output_tokens=settings.max_output_tokens)
                st.session_state.week4_benchmark = {"rows": rows, "details": details}
            except Exception as exc:  # noqa: BLE001
                show_error("Benchmark", exc)
        benchmark = st.session_state.get("week4_benchmark")
        if benchmark:
            rows = benchmark["rows"]
            passed = sum(r["Tool selection"] == "PASS" for r in rows) + sum(r["Arguments"] == "PASS" for r in rows)
            metric_row({"Checks passed": f"{passed} / {len(rows) * 2}",
                        "Tool selection": f"{sum(r['Tool selection'] == 'PASS' for r in rows)} / {len(rows)}",
                        "Arguments": f"{sum(r['Arguments'] == 'PASS' for r in rows)} / {len(rows)}"})
            st.dataframe(rows, width="stretch", hide_index=True)
            with st.expander("Benchmark responses"):
                st.json(benchmark["details"])
