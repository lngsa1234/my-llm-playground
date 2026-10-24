
import os
import time

import streamlit as st
from openai import OpenAI
from pydantic import create_model


# =========================================
# 1. APP SETUP
# =========================================

st.set_page_config(
    page_title="LLM Playground",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 LLM Playground")
st.caption(
    "Week 1 — Explore LLM API requests, "
    "structured output, token usage, and latency."
)

if not os.getenv("OPENAI_API_KEY"):
    st.error("OPENAI_API_KEY is not configured.")
    st.stop()

client = OpenAI()


# =========================================
# 2. BUILD A DYNAMIC OUTPUT SCHEMA
# =========================================

def build_output_model(schema_text):

    supported_types = {
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "list[str]": list[str],
    }

    fields = {}

    for line in schema_text.splitlines():

        line = line.strip()

        if not line:
            continue

        if ":" not in line:
            raise ValueError(
                f"Invalid field definition: {line}"
            )

        name, type_name = line.split(":", 1)

        name = name.strip()
        type_name = type_name.strip()

        if not name.isidentifier():
            raise ValueError(
                f"Invalid field name: {name}"
            )

        if type_name not in supported_types:
            raise ValueError(
                f"Unsupported type: {type_name}"
            )

        if name in fields:
            raise ValueError(
                f"Duplicate field: {name}"
            )

        fields[name] = (
            supported_types[type_name],
            ...
        )

    if not fields:
        raise ValueError(
            "Define at least one output field."
        )

    return create_model(
        "CustomOutput",
        **fields,
    )


# =========================================
# 3. SAVE THE LAST RESPONSE
# =========================================

if "last_result" not in st.session_state:
    st.session_state.last_result = None


# =========================================
# 4. TWO-COLUMN WEB LAYOUT
# =========================================

left_col, right_col = st.columns(
    [1, 1],
    gap="large",
)


# =========================================
# LEFT COLUMN: CONFIGURATION
# =========================================

with left_col:

    st.subheader("Configuration & Input")

    model = st.text_input(
        "Model",
        value="gpt-5.4-mini",
    )

    instructions = st.text_area(
        "System Instructions",
        value="You are a helpful AI assistant.",
        height=100,
    )

    prompt = st.text_area(
        "User Prompt",
        value=(
            "I'm a software engineer transitioning "
            "into AI product management. "
            "What skills should I develop?"
        ),
        height=140,
    )

    max_output_tokens = st.slider(
        "Maximum Output Tokens",
        min_value=100,
        max_value=3000,
        value=800,
        step=100,
    )

    st.divider()

    st.subheader("Output Format")

    output_format = st.radio(
        "Select output format",
        ["Text", "Structured JSON"],
        horizontal=True,
    )

    if output_format == "Structured JSON":

        schema_text = st.text_area(
            "Define JSON Fields",
            value=(
                "intent: str\n"
                "topic: str\n"
                "looking_for: str\n"
                "is_asking_for_connection: bool"
            ),
            height=140,
        )

        st.caption(
            "Supported types: str, int, "
            "float, bool, list[str]"
        )

    st.divider()

    with st.expander("Cost Settings (Optional)"):

        st.caption(
            "Enter the current price per "
            "million tokens for your model."
        )

        input_price = st.number_input(
            "Input price ($ / 1M tokens)",
            min_value=0.0,
            value=0.0,
            format="%.4f",
        )

        output_price = st.number_input(
            "Output price ($ / 1M tokens)",
            min_value=0.0,
            value=0.0,
            format="%.4f",
        )

    generate = st.button(
        "Generate Response",
        type="primary",
        use_container_width=True,
    )


# =========================================
# 5. EXECUTE THE API REQUEST
# =========================================

if generate:

    if not prompt.strip():
        st.warning("Please enter a user prompt.")

    else:

        try:

            start_time = time.perf_counter()

            if output_format == "Text":

                response = client.responses.create(
                    model=model,
                    instructions=instructions,
                    input=prompt,
                    max_output_tokens=max_output_tokens,
                )

                answer = response.output_text

            else:

                OutputModel = build_output_model(
                    schema_text
                )

                response = client.responses.parse(
                    model=model,
                    instructions=instructions,
                    input=prompt,
                    text_format=OutputModel,
                    max_output_tokens=max_output_tokens,
                )

                parsed = response.output_parsed

                answer = (
                    parsed.model_dump()
                    if parsed is not None
                    else None
                )

            latency = (
                time.perf_counter() - start_time
            )

            usage = response.usage

            input_tokens = usage.input_tokens
            output_tokens = usage.output_tokens
            total_tokens = usage.total_tokens

            estimated_cost = (
                input_tokens * input_price / 1_000_000
                + output_tokens * output_price / 1_000_000
            )

            st.session_state.last_result = {
                "answer": answer,
                "format": output_format,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "latency": latency,
                "estimated_cost": estimated_cost,
                "status": response.status,
                "incomplete_details": (
                    response.incomplete_details
                ),
                "raw_response": response.model_dump(),
            }

        except Exception as e:

            st.error(f"API request failed: {e}")


# =========================================
# RIGHT COLUMN: OUTPUT & METRICS
# =========================================

with right_col:

    st.subheader("Generated Response")

    result = st.session_state.last_result

    with st.container(border=True):

        if result is None:

            st.info(
                "Your response will appear here. "
                "Configure the request and click "
                "Generate Response."
            )

        elif result["answer"] is None:

            st.warning(
                "No parsed response was returned."
            )

        elif result["format"] == "Text":

            if result["answer"]:
                st.markdown(result["answer"])
            else:
                st.info("No visible text returned.")

        else:

            st.json(result["answer"])

    st.subheader("API Metrics")

    if result is not None:

        col1, col2 = st.columns(2)
        col3, col4 = st.columns(2)

        col1.metric(
            "Input Tokens",
            result["input_tokens"],
        )

        col2.metric(
            "Output Tokens",
            result["output_tokens"],
        )

        col3.metric(
            "Latency",
            f'{result["latency"]:.2f} s',
        )

        col4.metric(
            "Estimated Cost",
            f'${result["estimated_cost"]:.6f}',
        )

        st.write(
            "Total Tokens:",
            result["total_tokens"],
        )

        st.write(
            "Response Status:",
            result["status"],
        )

        if result["incomplete_details"]:

            st.warning(
                "Response incomplete: "
                f'{result["incomplete_details"]}'
            )

        with st.expander("Full API Response"):

            st.json(result["raw_response"])

    else:

        st.caption(
            "Token usage, latency, and cost "
            "will appear after your first request."
        )
