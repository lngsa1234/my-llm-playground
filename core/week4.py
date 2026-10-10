"""Week 4 Streamlit lab: a weather assistant with a real weather integration."""

from __future__ import annotations

import json
import os
import time
from typing import Any

import requests
import streamlit as st
from openai import OpenAI


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get the current weather for a city or location.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City or location to retrieve weather for.",
                }
            },
            "required": ["location"],
            "additionalProperties": False,
        },
    },
}
SYSTEM_PROMPT = (
    "You are a concise weather assistant. Use get_weather only for current weather "
    "in a named location. For comparisons, make one call for each city. Never invent "
    "weather values. Clearly report a tool error instead of making up data."
)
LOCATION_ALIASES = {
    "washington dc": "Washington, D.C.",
    "washington, dc": "Washington, D.C.",
    "washington d.c.": "Washington, D.C.",
    "washington, d.c.": "Washington, D.C.",
}


def get_weather(location: str) -> dict[str, Any]:
    """Geocode a place and retrieve its current Fahrenheit weather from Open-Meteo."""
    location = location.strip()
    if not location:
        return {"error": "Location is required."}
    lookup_location = LOCATION_ALIASES.get(location.casefold(), location)
    try:
        geocode = requests.get(
            GEOCODING_URL,
            params={"name": lookup_location, "count": 1, "language": "en", "format": "json"},
            timeout=10,
        )
        geocode.raise_for_status()
        results = geocode.json().get("results", [])
    except (requests.RequestException, ValueError):
        return {"error": "Weather service is temporarily unavailable."}
    if not results:
        return {"error": "Location not found."}

    place = results[0]
    try:
        weather = requests.get(
            FORECAST_URL,
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": "temperature_2m,apparent_temperature",
                "temperature_unit": "fahrenheit",
            },
            timeout=10,
        )
        weather.raise_for_status()
        current = weather.json()["current"]
        return {
            "location": place["name"],
            "state": place.get("admin1"),
            "country": place.get("country"),
            "temperature_f": current["temperature_2m"],
            "feels_like_f": current["apparent_temperature"],
        }
    except (KeyError, requests.RequestException, ValueError):
        return {"error": "Weather service is temporarily unavailable."}


def run_direct_agent(prompt: str, model: str) -> dict[str, Any]:
    """Run the runtime-owned tool loop and retain its trace for the lab UI."""
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    trace: list[dict[str, Any]] = []
    start = time.perf_counter()
    for _ in range(5):
        response = OpenAI().chat.completions.create(
            model=model, messages=messages, tools=[WEATHER_TOOL], tool_choice="auto"
        )
        assistant_message = response.choices[0].message
        messages.append(assistant_message.model_dump(exclude_none=True))
        if not assistant_message.tool_calls:
            return {
                "answer": assistant_message.content or "No visible answer was returned.",
                "trace": trace,
                "latency": time.perf_counter() - start,
            }
        for call in assistant_message.tool_calls:
            try:
                arguments = json.loads(call.function.arguments)
                result = get_weather(arguments["location"]) if call.function.name == "get_weather" else {"error": "Unsupported tool."}
            except (json.JSONDecodeError, KeyError, TypeError):
                result = {"error": "Invalid weather tool arguments."}
            trace.append({"tool": call.function.name, "arguments": call.function.arguments, "result": result})
            messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)})
    return {"answer": "Tool-call limit reached.", "trace": trace, "latency": time.perf_counter() - start}


def render_week4() -> None:
    """Render the Week 4 lab and expose the model/runtime boundary."""
    st.header("Week 4 · Weather Assistant")
    st.caption("Ask about current weather and inspect how the assistant uses live data.")

    assistant, evaluate = st.tabs(["Weather Assistant", "Evaluate"])
    with assistant:
        st.markdown(
            "The assistant can look up current weather for named locations. The trace below makes "
            "its live-data requests and returned results visible."
        )
        left, right = st.columns([3, 1])
        with left:
            prompt = st.text_area(
                "Try a prompt",
                "Which is warmer right now, Detroit or Miami?",
                key="week4_prompt",
                height=90,
            )
        with right:
            model = st.text_input("Model", os.getenv("OPENAI_MODEL", "gpt-4o-mini"), key="week4_model")
            run = st.button("Run weather agent", type="primary", use_container_width=True)
        if run:
            if not os.getenv("OPENAI_API_KEY"):
                st.error("OPENAI_API_KEY is not configured.")
            elif not prompt.strip() or not model.strip():
                st.warning("Enter both a prompt and model.")
            else:
                try:
                    with st.spinner("Model deciding; runtime executing any requested tools…"):
                        st.session_state.week4_result = run_direct_agent(prompt, model.strip())
                except Exception as exc:
                    st.error(f"Agent request failed: {type(exc).__name__}: {exc}")
        result = st.session_state.get("week4_result")
        if result:
            st.subheader("Final answer")
            st.write(result["answer"])
            count, latency = st.columns(2)
            count.metric("Tool calls", len(result["trace"]))
            latency.metric("Runtime latency", f"{result['latency']:.2f}s")
            with st.expander("Inspect runtime trace", expanded=True):
                if result["trace"]:
                    st.json(result["trace"])
                else:
                    st.info("No tool requested: this is the expected outcome for conceptual questions.")
        with st.expander("Tool schema supplied to the model"):
            st.json(WEATHER_TOOL)

    with evaluate:
        st.subheader("Evaluation prompts")
        st.dataframe(
            [
                {"Prompt": "What is weather?", "Expected behavior": "No tool call"},
                {"Prompt": "Explain humidity.", "Expected behavior": "No tool call"},
                {"Prompt": "Weather in Detroit now?", "Expected behavior": 'get_weather("Detroit")'},
                {"Prompt": "Weather in Miami?", "Expected behavior": 'get_weather("Miami")'},
                {"Prompt": "Detroit vs Miami right now?", "Expected behavior": "Two weather lookups"},
                {"Prompt": "Weather in invalid city?", "Expected behavior": "Tool call and graceful error"},
            ],
            use_container_width=True,
            hide_index=True,
        )
        st.subheader("What to assess")
        st.markdown(
            "1. **Tool selection** — was live weather data requested only when needed?\n"
            "2. **Argument accuracy** — did the request contain the intended location?\n"
            "3. **Execution success** — did the lookup return a usable result?\n"
            "4. **Task success** — did the final answer satisfy the question without inventing facts?"
        )
        st.info(
            "A correct `Location not found` result followed by an invented temperature is a task failure, "
            "not a successful assistant response."
        )
