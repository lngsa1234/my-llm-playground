"""Shared Streamlit building blocks so every week's page looks and behaves the same.

Page layout used by every week:

    Left sidebar     week navigation only (app.py)
    Main column      header → "How this lab works" → tabs / inputs → results
    Right panel      one box, one column:
                       ⚙️ Model settings  (same widgets, same keys, shared across weeks)
                       🧪 Lab parameters  (week-specific knobs)

Usage in a page:

    main, panel = page_layout(title, caption, how_it_works)
    settings = model_settings(panel)
    with lab_parameters(panel):
        ...widgets...
    with main:
        ...content...
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Callable

import streamlit as st

from labs.shared.settings import (
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_INPUT_PRICE,
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_MODEL,
    DEFAULT_OUTPUT_PRICE,
    ModelSettings,
    has_api_key,
)

SIDEBAR_WIDTH = 240
PANEL_RATIO = [3, 1]  # main column : right settings column


def apply_page_style() -> None:
    st.markdown(
        f"""
        <style>
            .block-container {{ padding-top: 2rem; }}
            [data-testid="stSidebar"] {{ min-width: {SIDEBAR_WIDTH}px; max-width: {SIDEBAR_WIDTH}px; }}
            [data-testid="stSidebar"] > div:first-child {{ width: {SIDEBAR_WIDTH}px; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, caption: str, how_it_works: str | None = None) -> None:
    """Standard page title, one-line caption and an optional collapsed explainer."""
    st.header(title)
    st.caption(caption)
    if how_it_works:
        with st.expander("How this lab works"):
            st.markdown(how_it_works)


def page_layout(title: str, caption: str, how_it_works: str | None = None):
    """Split the page into the main column and a full-height right-hand settings panel.

    The header and "How this lab works" go inside the main column, so the settings
    panel starts at the top of the page. Model settings and lab parameters share
    one bordered box, stacked in one column.
    """
    main, column = st.columns(PANEL_RATIO, gap="large")
    with main:
        page_header(title, caption, how_it_works)
    return main, column.container(border=True)


def model_settings(panel, *, max_tokens: bool = True, prices: bool = True, embedding: bool = False) -> ModelSettings:
    """Render the shared ⚙️ Model settings panel in the right column and return its values.

    The widget keys are the same on every page, so a model chosen in one week
    carries over to the next. Weeks hide the fields they don't use.
    """
    with panel:
        st.markdown("**⚙️ Model settings**")
        model = st.text_input("Model", DEFAULT_MODEL, key="settings_model").strip()
        embedding_model = (
            st.text_input("Embedding model", DEFAULT_EMBEDDING_MODEL, key="settings_embedding_model").strip()
            if embedding else DEFAULT_EMBEDDING_MODEL
        )
        max_output_tokens = (
            int(st.number_input("Max output tokens", 100, 8000, DEFAULT_MAX_OUTPUT_TOKENS, 100, key="settings_max_tokens"))
            if max_tokens else DEFAULT_MAX_OUTPUT_TOKENS
        )
        input_price, output_price = DEFAULT_INPUT_PRICE, DEFAULT_OUTPUT_PRICE
        if prices:
            input_price = st.number_input("Input $ / 1M tokens", 0.0, 100.0, DEFAULT_INPUT_PRICE, format="%.2f", key="settings_input_price")
            output_price = st.number_input("Output $ / 1M tokens", 0.0, 200.0, DEFAULT_OUTPUT_PRICE, format="%.2f", key="settings_output_price")
        if not has_api_key():
            st.warning("OPENAI_API_KEY is not set. Add it to `.env` and restart.")
    return ModelSettings(model=model, max_output_tokens=max_output_tokens, input_price=input_price,
                         output_price=output_price, embedding_model=embedding_model)


@contextmanager
def lab_parameters(panel):
    """The week's 🧪 Lab parameters, below Model settings in the same right-hand panel."""
    with panel:
        st.divider()
        st.markdown("**🧪 Lab parameters**")
        yield


def can_run(settings: ModelSettings, *required_text: str) -> bool:
    """Shared pre-flight check before any API call. Shows the reason when it fails."""
    if not has_api_key():
        st.error("OPENAI_API_KEY is not configured. Set it in `.env`, then restart Streamlit.")
        return False
    if not settings.model:
        st.warning("Enter a model in ⚙️ Model settings on the right.")
        return False
    if any(not text.strip() for text in required_text):
        st.warning("Fill in the required fields first.")
        return False
    return True


def metric_row(values: dict[str, str | int | float]) -> None:
    """A row of st.metric tiles; use '—' for values that don't exist yet."""
    for column, (label, value) in zip(st.columns(len(values)), values.items()):
        column.metric(label, value)


def usage_metrics(input_tokens=None, output_tokens=None, latency=None, cost=None) -> None:
    """The standard Input / Output / Latency / Cost tiles used across labs."""
    metric_row({
        "Input tokens": "—" if input_tokens is None else input_tokens,
        "Output tokens": "—" if output_tokens is None else output_tokens,
        "Latency": "—" if latency is None else f"{latency:.2f}s",
        "Cost": "—" if cost is None else f"${cost:.5f}",
    })


def show_error(stage: str, exc: Exception) -> None:
    """Show an API error with diagnostics, without exposing credentials."""
    details = {"stage": stage, "exception_type": type(exc).__name__, "message": str(exc)}
    for attribute in ("status_code", "code", "type", "request_id"):
        value = getattr(exc, attribute, None)
        if value is not None:
            details[attribute] = value
    headers = getattr(getattr(exc, "response", None), "headers", None)
    if headers:
        request_id = headers.get("x-request-id") or headers.get("request-id")
        if request_id and "request_id" not in details:
            details["request_id"] = request_id
    st.error(f"{stage} failed: {type(exc).__name__}: {exc}")
    with st.expander("Error details"):
        st.json(details)


def run_standalone(render: Callable[[], None], title: str) -> None:
    """Run one lab page as its own app: `streamlit run labs/<lab>/page.py`."""
    from dotenv import load_dotenv

    load_dotenv()
    st.set_page_config(page_title=title, page_icon="🧭", layout="wide")
    apply_page_style()
    render()
