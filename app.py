
import os
import time
import keyword

import streamlit as st
from openai import OpenAI
from pydantic import create_model


# =========================================
# 1. PAGE CONFIGURATION
# =========================================

st.set_page_config(
    page_title="LLM Playground",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Compact styling with extra top padding
# to prevent the page title from being clipped.

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 2.5rem;
            padding-bottom: 0.5rem;
            padding-left: 1.5rem;
            padding-right: 1.5rem;
            max-width: 100%;
        }

        div[data-testid="stVerticalBlock"] {
            gap: 0.5rem;
        }

        div[data-testid="stMetricValue"] {
            font-size: 1.3rem;
        }

        div[data-testid="stMetricLabel"] {
            font-size: 0.8rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================
# 2. PAGE HEADER
# =========================================

st.title("🤖 LLM Playground")

st.write(
    "Week 1 — Explore LLM API requests, "
    "structured output, token usage, and latency."
)


# =========================================
# 3. OPENAI CLIENT
# =========================================

if not os.getenv("OPENAI_API_KEY"):
    st.error(
        "OPENAI_API_KEY is not configured. "
        "Set it in Terminal before launching Streamlit."
    )
    st.stop()

client = OpenAI()


# =========================================
# 4. DYNAMIC JSON OUTPUT MODEL
# =========================================

def build_output_model(schema_text):
    """
    Convert user-defined fields into a Pydantic model.

    Example:
        intent: str
        confidence: float
        is_valid: bool
    """

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

        if (
            not name.isidentifier()
            or keyword.iskeyword(name)
            or name.startswith("_")
        ):
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
            "Define at least one JSON field."
        )

    return create_model(
        "CustomOutput",
        **fields,
    )


# =========================================
# 5. SESSION STATE
# =========================================

if "last_result" not in st.session_state:
    st.session_state.last_result = None


# =========================================
# 6. TWO-COLUMN LAYOUT
# =========================================

left_col, right_col = st.columns(
    [1, 1],
    gap="large",
)


# =========================================
# LEFT COLUMN: CONFIGURATION & INPUT
# =========================================

with left_col:

    st.subheader("Configuration & Input")

    # Model and token limit on one row
    model_col, token_col = st.columns(2)

    with model_col:

        model = st.text_input(
            "Model",
            value="gpt-5.4-mini",
        )

    with token_col:

        max_output_tokens = st.number_input(
            "Max Output Tokens",
            min_value=100,
            max_value=10000,
            value=800,
            step=100,
        )

    # System instructions
    instructions = st.text_area(
        "System Instructions",
        value="You are a helpful AI assistant.",
        height=68,
    )

    # User prompt
    prompt = st.text_area(
        "User Prompt",
        value=(
            "I'm a software engineer transitioning "
            "into AI product management. "
            "What skills should I develop?"
        ),
        height=100,
    )

    # Output format
    output_format = st.radio(
        "Output Format",
        ["Text", "Structured JSON"],
        horizontal=True,
    )

    # JSON schema configuration
    if output_format == "Structured JSON":

        schema_text = st.text_area(
            "JSON Fields",
            value=(
                "intent: str\n"
                "topic: str\n"
                "looking_for: str\n"
                "is_asking_for_connection: bool"
            ),
            height=95,
        )

        st.caption(
            "Supported types: str, int, "
            "float, bool, list[str]"
        )

    # Cost configuration
    with st.expander("Cost Settings (Optional)"):

        st.caption(
            "Enter the current standard, uncached "
            "prices per million tokens for your model."
        )

        input_price = st.number_input(
            "Input price ($ / 1M tokens)",
            min_value=0.0,
            value=0.75,
            format="%.4f",
        )

        output_price = st.number_input(
            "Output price ($ / 1M tokens)",
            min_value=0.0,
            value=4.50,
            format="%.4f",
        )

    # Generate button
    generate = st.button(
        "Generate Response",
        type="primary",
        use_container_width=True,
    )


# =========================================
# 7. EXECUTE API REQUEST
# =========================================

if generate:

    if not prompt.strip():

        st.warning("Please enter a user prompt.")

    elif not model.strip():

        st.warning("Please enter a model ID.")

    else:

        try:

            with st.spinner("Generating response..."):

                start_time = time.perf_counter()

                # -----------------------------
                # TEXT OUTPUT
                # -----------------------------

                if output_format == "Text":

                    response = client.responses.create(
                        model=model.strip(),
                        instructions=instructions,
                        input=prompt,
                        max_output_tokens=int(
                            max_output_tokens
                        ),
                    )

                    answer = response.output_text

                # -----------------------------
                # STRUCTURED JSON OUTPUT
                # -----------------------------

                else:

                    OutputModel = build_output_model(
                        schema_text
                    )

                    response = client.responses.parse(
                        model=model.strip(),
                        instructions=instructions,
                        input=prompt,
                        text_format=OutputModel,
                        max_output_tokens=int(
                            max_output_tokens
                        ),
                    )

                    parsed = response.output_parsed

                    answer = (
                        parsed.model_dump()
                        if parsed is not None
                        else None
                    )

                # -----------------------------
                # LATENCY
                # -----------------------------

                latency = (
                    time.perf_counter() - start_time
                )

                # -----------------------------
                # TOKEN USAGE
                # -----------------------------

                usage = response.usage

                input_tokens = usage.input_tokens
                output_tokens = usage.output_tokens
                total_tokens = usage.total_tokens

                # -----------------------------
                # ESTIMATED COST
                # -----------------------------

                estimated_cost = (
                    input_tokens
                    * input_price
                    / 1_000_000
                    +
                    output_tokens
                    * output_price
                    / 1_000_000
                )

                # -----------------------------
                # SAVE RESULT
                # -----------------------------

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
                    "raw_response": (
                        response.model_dump()
                    ),
                }

        except Exception as e:

            st.error(f"API request failed: {e}")


# =========================================
# RIGHT COLUMN: METRICS FIRST
# =========================================

with right_col:

    result = st.session_state.last_result

    # -------------------------------------
    # 1. API METRICS
    # -------------------------------------

    st.subheader("API Metrics")

    m1, m2, m3, m4 = st.columns(4)

    if result is not None:

        m1.metric(
            "Input",
            result["input_tokens"],
        )

        m2.metric(
            "Output",
            result["output_tokens"],
        )

        m3.metric(
            "Latency",
            f'{result["latency"]:.2f}s',
        )

        m4.metric(
            "Cost",
            f'${result["estimated_cost"]:.5f}',
        )

        st.caption(
            f'Total tokens: {result["total_tokens"]}'
            f'  |  Status: {result["status"]}'
        )

        if result["incomplete_details"]:

            st.warning(
                "Response incomplete: "
                f'{result["incomplete_details"]}'
            )

    else:

        m1.metric("Input", "—")
        m2.metric("Output", "—")
        m3.metric("Latency", "—")
        m4.metric("Cost", "—")

        st.caption(
            "Metrics will appear after generation."
        )

    # -------------------------------------
    # 2. GENERATED RESPONSE
    # -------------------------------------

    st.subheader("Generated Response")

    with st.container(border=True):

        if result is None:

            st.caption(
                "Your generated response will "
                "appear here."
            )

        elif result["answer"] is None:

            st.warning(
                "No parsed response was returned."
            )

        elif result["format"] == "Text":

            if result["answer"]:

                st.markdown(result["answer"])

            else:

                st.info(
                    "No visible text returned."
                )

        else:

            st.json(result["answer"])

    # -------------------------------------
    # 3. FULL API RESPONSE
    # -------------------------------------

    if result is not None:

        with st.expander("Full API Response"):

            st.json(result["raw_response"])
