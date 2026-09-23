"""The Week 1 single-call playground tab."""

import os
import time
import keyword

import streamlit as st
from openai import OpenAI
from pydantic import create_model


def build_output_model(schema_text: str):
    """Build a small Pydantic schema from editable `name: type` fields."""
    supported = {"str": str, "int": int, "float": float, "bool": bool, "list[str]": list[str]}
    fields = {}
    for raw_line in schema_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if ":" not in line:
            raise ValueError(f"Use `name: type` for every field: {line}")
        name, type_name = (part.strip() for part in line.split(":", 1))
        if not name.isidentifier() or keyword.iskeyword(name) or name.startswith("_"):
            raise ValueError(f"Invalid field name: {name}")
        if type_name not in supported:
            raise ValueError(f"Unsupported type: {type_name}")
        if name in fields:
            raise ValueError(f"Duplicate field: {name}")
        fields[name] = (supported[type_name], ...)
    if not fields:
        raise ValueError("Define at least one JSON field.")
    return create_model("Week1Output", **fields)


def render_week1() -> None:
    st.header("Week 1: Single API Call")
    st.caption("Explore one independent API call, its response, token use, latency, and estimated cost.")
    if "week1_result" not in st.session_state:
        st.session_state.week1_result = None
    left, right = st.columns(2, gap="large")
    with left:
        model = st.text_input("Model", "gpt-5.4-mini", key="week1_model")
        instructions = st.text_area("System instructions", "You are a helpful AI assistant.", key="week1_instructions")
        prompt = st.text_area("User prompt", "Explain the difference between context and a prompt in simple language.", key="week1_prompt")
        output_format = st.radio("Output format", ["Text", "Structured Output"], horizontal=True, key="week1_format")
        if output_format == "Structured Output":
            schema_text = st.text_area("Structured output fields", "concept: str\nexplanation: str\nexample: str", key="week1_schema")
            st.caption("Use `name: type`. Supported: str, int, float, bool, list[str].")
        maximum = st.number_input("Max output tokens", 100, 4000, 800, 100, key="week1_tokens")
        input_price = st.number_input("Input $ / 1M tokens", 0.0, 0.75, format="%.4f", key="week1_in_price")
        output_price = st.number_input("Output $ / 1M tokens", 0.0, 4.50, format="%.4f", key="week1_out_price")
        if st.button("Generate response", type="primary", use_container_width=True, key="week1_run"):
            if not os.getenv("OPENAI_API_KEY"):
                st.error("OPENAI_API_KEY is not configured. Set it, then restart Streamlit.")
            elif not model.strip() or not prompt.strip():
                st.warning("Enter a model and prompt.")
            else:
                try:
                    with st.spinner("Generating response…"):
                        start = time.perf_counter()
                        if output_format == "Structured Output":
                            response = OpenAI().responses.parse(model=model.strip(), instructions=instructions, input=prompt, text_format=build_output_model(schema_text), max_output_tokens=int(maximum))
                            answer = response.output_parsed.model_dump() if response.output_parsed else None
                        else:
                            response = OpenAI().responses.create(model=model.strip(), instructions=instructions, input=prompt, max_output_tokens=int(maximum))
                            answer = response.output_text
                    usage = response.usage
                    st.session_state.week1_result = {"answer": answer, "format": output_format, "input": usage.input_tokens, "output": usage.output_tokens, "total": usage.total_tokens, "latency": time.perf_counter() - start, "cost": usage.input_tokens * input_price / 1_000_000 + usage.output_tokens * output_price / 1_000_000, "status": response.status}
                except Exception as exc:
                    st.error(f"API request failed: {exc}")
    with right:
        result = st.session_state.week1_result
        st.subheader("Metrics")
        a, b, c, d = st.columns(4)
        if result is None:
            a.metric("Input", "—")
            b.metric("Output", "—")
            c.metric("Latency", "—")
            d.metric("Cost", "—")
        else:
            a.metric("Input", result["input"])
            b.metric("Output", result["output"])
            c.metric("Latency", f"{result['latency']:.2f}s")
            d.metric("Cost", f"${result['cost']:.5f}")
            st.caption(f"Total tokens: {result['total']} · Status: {result['status']}")
        st.subheader("Response")
        if result is None:
            st.info("Your API response will appear here.")
        elif result["format"] == "Structured Output":
            st.json(result["answer"])
        else:
            st.markdown(result["answer"] or "_No visible text returned._")
