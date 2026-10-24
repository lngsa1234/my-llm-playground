"""Week 1 page: a single LLM API call."""

from __future__ import annotations

import json

import streamlit as st

from core.week1.playground import run_single_call
from ui.components import can_run, lab_parameters, model_settings, page_header, show_error, usage_metrics

HOW_IT_WORKS = """
1. Your **system instructions** and **user prompt** are sent in one API request, with the model and max output tokens from ⚙️ Model settings.
2. With **Structured output**, the fields you define become a JSON schema the response must follow.
3. The response comes back with token counts. Latency is measured around the call, and cost uses the prices in ⚙️ Model settings.
4. Nothing is remembered between calls: each run is independent.
"""


def render() -> None:
    page_header("Week 1 · Single API Call",
                "Explore one independent API call: its response, token use, latency and estimated cost.",
                HOW_IT_WORKS)
    settings = model_settings()
    with lab_parameters():
        output_format = st.radio("Output format", ["Text", "Structured output"], horizontal=True, key="week1_format")
        schema_text = None
        if output_format == "Structured output":
            schema_text = st.text_area("Output fields", "concept: str\nexplanation: str\nexample: str", key="week1_schema")
            st.caption("One `name: type` per line. Types: str, int, float, bool, list[str].")

    left, right = st.columns(2, gap="large")
    with left:
        instructions = st.text_area("System instructions", "You are a helpful AI assistant.", key="week1_instructions")
        prompt = st.text_area("User prompt", "Explain the difference between context and a prompt in simple language.",
                              key="week1_prompt", height=120)
        if st.button("Generate response", type="primary", width="stretch", key="week1_run"):
            if can_run(settings, prompt):
                try:
                    with st.spinner("Generating response…"):
                        st.session_state.week1_result = run_single_call(settings, instructions, prompt, schema_text)
                except Exception as exc:  # noqa: BLE001
                    show_error("API request", exc)

    with right:
        result = st.session_state.get("week1_result")
        st.subheader("Metrics")
        if result:
            usage_metrics(result["input_tokens"], result["output_tokens"], result["latency"], result["cost"])
            st.caption(f"Total tokens: {result['total_tokens']} · Status: {result['status']}")
        else:
            usage_metrics()
        st.subheader("Response")
        if result is None:
            st.info("Your API response will appear here.")
        elif result["structured"]:
            st.code(json.dumps(result["answer"], indent=2), language="json")
        else:
            st.info(result["answer"] or "No visible text returned.")
