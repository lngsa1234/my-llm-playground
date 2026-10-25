"""Shared Streamlit building blocks so every week's page looks and behaves the same.

Page layout used by every week:

    Left sidebar     week navigation only (app.py)
    Main column      title → part switch (Concept demo | Build Mini Muse) →
                       Concept demo:    caption → "How this lab works" → inputs → results
                       Build Mini Muse: the step's own caption → "How this step works" → inputs → results
    Right panel      one box, one column:
                       Model settings   the model; "Model options" folds away tokens and prices
                       Lab parameters   the week's own controls

Usage in a page:

    main, panel = page_layout(title)
    if mini_muse_part(main, panel, week, caption=caption, how_it_works=how_it_works):
        return  # the Mini Muse step drew itself
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


def page_header(title: str, caption: str | None = None, how_it_works: str | None = None,
                how_label: str = "How this lab works") -> None:
    """Standard page title, one-line caption and an optional collapsed explainer."""
    st.header(title)
    if caption:
        st.caption(caption)
    if how_it_works:
        with st.expander(how_label):
            st.markdown(how_it_works)


def page_layout(title: str, caption: str | None = None, how_it_works: str | None = None,
                how_label: str = "How this lab works"):
    """Split the page into the main column and a full-height right-hand settings panel.

    The header and "How this lab works" go inside the main column, so the settings
    panel starts at the top of the page. Model settings and lab parameters share
    one bordered box, stacked in one column.
    """
    main, column = st.columns(PANEL_RATIO, gap="large")
    with main:
        page_header(title, caption, how_it_works, how_label)
    return main, column.container(border=True)


def model_settings(panel, *, max_tokens: bool = True, prices: bool = True, embedding: bool = False) -> ModelSettings:
    """Render the shared Model settings at the top of the right column and return their values.

    Only the model is always visible; token limit, prices and the embedding model sit in
    "Model options". The widget keys are the same on every page, so a choice made in one
    week carries over to the next. Weeks hide the fields they don't use.
    """
    with panel:
        st.markdown("**Model settings**")
        model = st.text_input("Model", DEFAULT_MODEL, key="settings_model").strip()
        embedding_model, max_output_tokens = DEFAULT_EMBEDDING_MODEL, DEFAULT_MAX_OUTPUT_TOKENS
        input_price, output_price = DEFAULT_INPUT_PRICE, DEFAULT_OUTPUT_PRICE
        if embedding or max_tokens or prices:
            with st.expander("Model options"):
                if embedding:
                    embedding_model = st.text_input("Embedding model", DEFAULT_EMBEDDING_MODEL,
                                                    key="settings_embedding_model").strip()
                if max_tokens:
                    max_output_tokens = int(st.number_input("Max output tokens", 100, 8000, DEFAULT_MAX_OUTPUT_TOKENS,
                                                            100, key="settings_max_tokens"))
                if prices:
                    input_price = st.number_input("Input $ / 1M tokens", 0.0, 100.0, DEFAULT_INPUT_PRICE,
                                                  format="%.2f", key="settings_input_price")
                    output_price = st.number_input("Output $ / 1M tokens", 0.0, 200.0, DEFAULT_OUTPUT_PRICE,
                                                   format="%.2f", key="settings_output_price")
    return ModelSettings(model=model, max_output_tokens=max_output_tokens, input_price=input_price,
                         output_price=output_price, embedding_model=embedding_model)


def api_key_notice() -> None:
    """Shown once, in the sidebar, instead of on every page."""
    if not has_api_key():
        st.warning("No OpenAI API key is set, so model calls won't run. Add `OPENAI_API_KEY` to `.env` "
                   "and restart.")


@contextmanager
def lab_parameters(panel):
    """The week's Lab parameters, below Model settings in the same right-hand panel."""
    with panel:
        st.divider()
        st.markdown("**Lab parameters**")
        yield


def can_run(settings: ModelSettings, *required_text: str) -> bool:
    """Shared pre-flight check before any API call. Shows the reason when it fails."""
    if not has_api_key():
        st.error("OPENAI_API_KEY is not configured. Set it in `.env`, then restart Streamlit.")
        return False
    if not settings.model:
        st.warning("Enter a model in Model settings on the right.")
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


def usage_line(input_tokens: int, output_tokens: int, latency: float | None, cost: float) -> None:
    """The same numbers as usage_metrics, as one quiet line for narrow boxes."""
    parts = [f"{input_tokens:,} input tokens", f"{output_tokens:,} output tokens"]
    if latency is not None:
        parts.append(f"{latency:.2f} s")
    parts.append(f"${cost:.5f}")
    st.caption(" · ".join(parts))


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
    with st.sidebar:
        api_key_notice()
    render()


CONCEPT_PART = "Concept demo"
MINI_MUSE_PART = "Build Mini Muse"
PARTS = [CONCEPT_PART, MINI_MUSE_PART]


def _keep_part(key: str) -> None:
    """Clicking the selected option clears a segmented control; keep the last choice instead."""
    if st.session_state.get(key) is None:
        st.session_state[key] = st.session_state.get(f"{key}_last", CONCEPT_PART)
    st.session_state[f"{key}_last"] = st.session_state[key]


def mini_muse_part(main, panel, week: int, caption: str | None = None, how_it_works: str | None = None,
                   **settings_options) -> bool:
    """The switch at the top of each week page: the week's concept demo, or its Mini Muse step.

    When the Mini Muse step is chosen, this renders it (with its own Model settings and
    Lab parameters) and returns True, so the page can stop there:

        if mini_muse_part(main, panel, 1):
            return
    """
    key = f"week{week}_part"
    if key not in st.session_state:  # back on this week: show the part that was open
        st.session_state[key] = st.session_state.get(f"{key}_last", CONCEPT_PART)
    with main:
        part = st.segmented_control("Part", PARTS, key=key, label_visibility="collapsed",
                                    on_change=_keep_part, args=(key,)) or CONCEPT_PART
    st.session_state[f"{key}_last"] = part
    if part != MINI_MUSE_PART:
        with main:
            if caption:
                st.caption(caption)
            if how_it_works:
                with st.expander("How this lab works"):
                    st.markdown(how_it_works)
        return False
    from mini_muse.page import render_step  # the project's screens live with its code, in mini_muse/

    render_step(week, main, panel, model_settings(panel, **settings_options))
    return True


OWN_TEXT = "(write your own)"


def example_text_area(label: str, examples: list[str], key: str, height: int = 70) -> str:
    """An "Examples" picker that fills a text box, and survives leaving the page.

    Streamlit forgets a widget's value when that widget is not drawn (another week,
    or the other part of this page), but keeps plain session values. So the picked
    example and the box's text are also saved under plain keys, and restored on return.
    """
    pick_key, text_key, saved_key, last_key = f"{key}_example", f"{key}_text", f"{key}_saved", f"{key}_last_example"
    options = examples + [OWN_TEXT]
    if pick_key not in st.session_state and st.session_state.get(last_key) in options:
        st.session_state[pick_key] = st.session_state[last_key]
    choice = st.selectbox("Examples", options, key=pick_key)
    if st.session_state.get(last_key) != choice:  # a different example was picked: fill the box with it
        st.session_state[text_key] = "" if choice == OWN_TEXT else choice
        st.session_state[last_key] = choice
    elif text_key not in st.session_state:  # back on the page: restore what the box held
        st.session_state[text_key] = st.session_state.get(saved_key, "" if choice == OWN_TEXT else choice)
    text = st.text_area(label, key=text_key, height=height)
    st.session_state[saved_key] = text
    return text
