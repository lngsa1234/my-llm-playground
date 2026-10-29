"""Week 1 page: a single LLM API call.

Run alone:   streamlit run labs/week1_llm_api/page.py
In the site: streamlit run app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Lets this page run on its own (streamlit run labs/<lab>/page.py) as well as inside app.py.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import json

import streamlit as st

from labs.week1_llm_api.playground import run_single_call
from labs.shared.ui import mini_muse_part, can_run, lab_parameters, model_settings, page_layout, show_error, usage_line, run_standalone

HOW_IT_WORKS = """
1. Your **system instructions** and **user prompt** are sent in one API request, with the model and max output tokens from Model settings.
2. With **Structured output**, the fields you define become a JSON schema the response must follow.
3. The response comes back with token counts. Latency is measured around the call, and cost uses the prices in Model settings.
4. Nothing is remembered between calls: each run is independent.
"""


def render() -> None:
    main, panel = page_layout("Week 1 · Single API call")
    settings = model_settings(panel)
    if mini_muse_part(main, panel, 1,
                      caption="Send one request to a model and see exactly what comes back: the response, tokens, latency and cost.",
                      how_it_works=HOW_IT_WORKS):
        return
    with lab_parameters(panel):
        output_format = st.radio("Output format", ["Text", "Structured output"], horizontal=True, key="week1_format")
        schema_text = None
        if output_format == "Structured output":
            schema_text = st.text_area("Output fields", "concept: str\nexplanation: str\nexample: str", key="week1_schema")
            st.caption("One `name: type` per line. Types: str, int, float, bool, list[str].")

    with main:
        left, right = st.columns(2, gap="large")
        with left:
            instructions = st.text_area("System instructions", "You are a helpful AI assistant.", key="week1_instructions")
            prompt = st.text_area("User prompt", "Explain the difference between context and a prompt in simple language.",
                                  key="week1_prompt", height=120)
            if st.button("Send request", type="primary", width="stretch", key="week1_run"):
                if can_run(settings, prompt):
                    try:
                        with st.spinner("Waiting for the model…"):
                            st.session_state.week1_result = run_single_call(settings, instructions, prompt, schema_text)
                    except Exception as exc:  # noqa: BLE001
                        show_error("API request", exc)

        with right, st.container(border=True):
            result = st.session_state.get("week1_result")
            st.markdown("**Response**")
            if result is None:
                st.caption("Send a request to see the response, its tokens and its cost here.")
            else:
                if result["structured"]:
                    st.code(json.dumps(result["answer"], indent=2), language="json")
                else:
                    st.markdown(result["answer"] or "_No visible text returned._")
                usage_line(result["input_tokens"], result["output_tokens"], result["latency"], result["cost"])


if __name__ == "__main__":
    run_standalone(render, "Week 1 · Single API call")
