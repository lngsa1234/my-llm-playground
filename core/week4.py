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


LIVE_BENCHMARKS = [
    {"prompt": "What is weather?", "locations": []},
    {"prompt": "Weather in Detroit now?", "locations": ["Detroit"]},
    {"prompt": "Detroit vs Miami right now?", "locations": ["Detroit", "Miami"]},
]


def run_live_benchmark(model: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Score a small live set for tool selection and location arguments."""
    rows: list[dict[str, Any]] = []
    details: list[dict[str, Any]] = []
    for case in LIVE_BENCHMARKS:
        result = run_direct_agent(case["prompt"], model)
        actual_locations = []
        for entry in result["trace"]:
            try:
                actual_locations.append(json.loads(entry["arguments"])["location"])
            except (json.JSONDecodeError, KeyError, TypeError):
                actual_locations.append("<invalid arguments>")
        expected_locations = case["locations"]
        selection_passed = len(result["trace"]) == len(expected_locations)
        arguments_passed = [item.casefold() for item in actual_locations] == [item.casefold() for item in expected_locations]
        rows.append(
            {
                "Prompt": case["prompt"],
                "Expected calls": len(expected_locations),
                "Actual calls": len(result["trace"]),
                "Tool selection": "PASS" if selection_passed else "FAIL",
                "Arguments": "PASS" if arguments_passed else "FAIL",
            }
        )
        details.append({"prompt": case["prompt"], **result})
    return rows, details


def render_week4() -> None:
    """Render the Week 4 weather assistant and its benchmark results."""
    st.header("Week 4 · Weather Assistant")
    st.caption("Ask about current weather and inspect how the assistant uses live data.")

    st.markdown("The assistant can look up current weather for named locations. The trace below makes its live-data requests and returned results visible.")
    left, right = st.columns([3, 1])
    with left:
        prompt = st.text_area("Try a prompt", "Which is warmer right now, Detroit or Miami?", key="week4_prompt", height=90)
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

    st.divider()
    st.subheader("Benchmark results")
    st.caption("Run three prompts against the selected model to measure tool selection and location arguments. This makes OpenAI and weather-provider requests.")
    if st.button("Run live benchmark", use_container_width=True):
        if not os.getenv("OPENAI_API_KEY"):
            st.error("OPENAI_API_KEY is not configured.")
        elif not model.strip():
            st.warning("Enter a model first.")
        else:
            try:
                with st.spinner("Running 3 benchmark prompts…"):
                    rows, details = run_live_benchmark(model.strip())
                st.session_state.week4_benchmark = {"rows": rows, "details": details}
            except Exception as exc:
                st.error(f"Benchmark failed: {type(exc).__name__}: {exc}")
    benchmark = st.session_state.get("week4_benchmark")
    if benchmark:
        rows = benchmark["rows"]
        total = len(rows) * 2
        passed = sum(row["Tool selection"] == "PASS" for row in rows) + sum(row["Arguments"] == "PASS" for row in rows)
        st.metric("Live benchmark checks", f"{passed} / {total} passed")
        st.dataframe(rows, use_container_width=True, hide_index=True)
        with st.expander("Inspect benchmark responses"):
            st.json(benchmark["details"])
