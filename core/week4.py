"""Week 4 Streamlit lab: a weather assistant with a real weather integration."""

from __future__ import annotations

import json
import os
import time
from datetime import date, timedelta
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
WEEKEND_FORECAST_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "get_weekend_forecast",
        "description": (
            "Get the daily forecast for the upcoming Saturday and Sunday in a named "
            "location. Use this for requests about this weekend or choosing a weekend day."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City or location to retrieve the weekend forecast for.",
                }
            },
            "required": ["location"],
            "additionalProperties": False,
        },
    },
}
LOCATION_ALIASES = {
    "washington dc": "Washington, D.C.",
    "washington, dc": "Washington, D.C.",
    "washington d.c.": "Washington, D.C.",
    "washington, d.c.": "Washington, D.C.",
}
LEGACY_DEFAULT_PROMPT = "Which is warmer right now, Detroit or Miami?"
DEFAULT_PROMPT = (
    "I want to take my kids hiking this weekend in Detroit. Which day is better? "
    "I don't like rain and ideally it should be above 60°F."
)


def upcoming_weekend(today: date | None = None) -> tuple[date, date]:
    """Return the Saturday and Sunday referred to as the upcoming weekend."""
    today = today or date.today()
    days_until_saturday = (5 - today.weekday()) % 7
    saturday = today + timedelta(days=days_until_saturday)
    return saturday, saturday + timedelta(days=1)


def system_prompt(today: date | None = None) -> str:
    """Build instructions with a date so relative time is never left to the model."""
    saturday, sunday = upcoming_weekend(today)
    return (
        "You are a concise weather assistant. Never invent weather values; clearly report "
        "a tool error instead. Use get_weather for current conditions in a named location. "
        "Use get_weekend_forecast for requests about this weekend or for selecting a weekend "
        "day. Today is "
        f"{(today or date.today()).isoformat()}; 'this weekend' means {saturday.strftime('%A, %B %-d')} "
        f"and {sunday.strftime('%A, %B %-d')}. Do not ask for dates when the user says 'this "
        "weekend.' If a location is missing, ask only for the location. For hiking recommendations, "
        "compare both days against the user's preferences (including rain and temperature) and "
        "recommend the better day, noting any tradeoff."
    )


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


def get_weekend_forecast(location: str, today: date | None = None) -> dict[str, Any]:
    """Geocode a place and retrieve daily Fahrenheit forecasts for the upcoming weekend."""
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

    saturday, sunday = upcoming_weekend(today)
    place = results[0]
    try:
        weather = requests.get(
            FORECAST_URL,
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max",
                "temperature_unit": "fahrenheit",
                "forecast_days": 16,
                "timezone": "auto",
            },
            timeout=10,
        )
        weather.raise_for_status()
        daily = weather.json()["daily"]
        by_day = {
            forecast_date: index for index, forecast_date in enumerate(daily["time"])
        }
        forecast = []
        for forecast_day in (saturday, sunday):
            index = by_day[forecast_day.isoformat()]
            forecast.append(
                {
                    "date": forecast_day.isoformat(),
                    "day": forecast_day.strftime("%A"),
                    "high_f": daily["temperature_2m_max"][index],
                    "low_f": daily["temperature_2m_min"][index],
                    "precipitation_probability_max": daily["precipitation_probability_max"][index],
                    "precipitation_sum_in": daily["precipitation_sum"][index] / 25.4,
                }
            )
        return {
            "location": place["name"],
            "state": place.get("admin1"),
            "country": place.get("country"),
            "forecast": forecast,
        }
    except (KeyError, IndexError, TypeError, requests.RequestException, ValueError):
        return {
            "error": "The weather service does not have a forecast for the upcoming weekend yet."
        }


def run_direct_agent(prompt: str, model: str, use_tools: bool = True) -> dict[str, Any]:
    """Run the agent with optional weather tools and retain its trace for the lab UI."""
    instructions = system_prompt()
    if not use_tools:
        instructions = (
            "You are a concise weather assistant operating without access to live weather data. "
            "Do not invent weather values or recommendations based on a forecast. Explain briefly "
            "that current or forecast data is needed to answer location- and date-specific questions."
        )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": instructions},
        {"role": "user", "content": prompt},
    ]
    trace: list[dict[str, Any]] = []
    start = time.perf_counter()
    for _ in range(5):
        request: dict[str, Any] = {"model": model, "messages": messages}
        if use_tools:
            request.update({"tools": [WEATHER_TOOL, WEEKEND_FORECAST_TOOL], "tool_choice": "auto"})
        response = OpenAI().chat.completions.create(**request)
        assistant_message = response.choices[0].message
        messages.append(assistant_message.model_dump(exclude_none=True))
        if not assistant_message.tool_calls:
            return {
                "answer": assistant_message.content or "No visible answer was returned.",
                "trace": trace,
                "latency": time.perf_counter() - start,
                "mode": "With tools" if use_tools else "Without tools",
            }
        for call in assistant_message.tool_calls:
            try:
                arguments = json.loads(call.function.arguments)
                if call.function.name == "get_weather":
                    result = get_weather(arguments["location"])
                elif call.function.name == "get_weekend_forecast":
                    result = get_weekend_forecast(arguments["location"])
                else:
                    result = {"error": "Unsupported tool."}
            except (json.JSONDecodeError, KeyError, TypeError):
                result = {"error": "Invalid weather tool arguments."}
            trace.append({"tool": call.function.name, "arguments": call.function.arguments, "result": result})
            messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)})
    return {
        "answer": "Tool-call limit reached.",
        "trace": trace,
        "latency": time.perf_counter() - start,
        "mode": "With tools" if use_tools else "Without tools",
    }


LIVE_BENCHMARKS = [
    {"prompt": "What is weather?", "locations": []},
    {"prompt": "Explain humidity.", "locations": []},
    {"prompt": "Weather in Detroit now?", "locations": ["Detroit"]},
    {"prompt": "What's the current weather in Miami?", "locations": ["Miami"]},
    {"prompt": "What's the weather in Washington DC?", "locations": ["Washington DC"]},
    {"prompt": "Detroit vs Miami right now?", "locations": ["Detroit", "Miami"]},
    {"prompt": "Which is warmer right now: Detroit, Miami, or Chicago?", "locations": ["Detroit", "Miami", "Chicago"]},
    {"prompt": "I am flying from Seattle to Phoenix today. Which city is warmer right now, and by how much?", "locations": ["Seattle", "Phoenix"]},
    {"prompt": "Should I pack a jacket? Give the current temperature and feels-like temperature for Anchorage, Alaska and Honolulu, Hawaii.", "locations": ["Anchorage, Alaska", "Honolulu, Hawaii"]},
    {"prompt": "How much warmer does Miami feel than Chicago right now?", "locations": ["Miami", "Chicago"]},
    {"prompt": "Compare the current weather in Portland, Oregon and Portland, Maine. Keep the two cities distinct.", "locations": ["Portland, Oregon", "Portland, Maine"]},
    {"prompt": "What are the current conditions in São Paulo, Brazil and Reykjavík, Iceland?", "locations": ["São Paulo, Brazil", "Reykjavík, Iceland"]},
    {"prompt": "Do not look up weather. Explain in general why coastal and inland cities can have different temperatures.", "locations": []},
    {"prompt": "What's the weather in asdfghxyz?", "locations": ["asdfghxyz"]},
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
        canonical_actual = [LOCATION_ALIASES.get(item.casefold(), item).casefold() for item in actual_locations]
        canonical_expected = [LOCATION_ALIASES.get(item.casefold(), item).casefold() for item in expected_locations]
        arguments_passed = canonical_actual == canonical_expected
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
    st.caption("Ask about current conditions or which upcoming-weekend day is best, and inspect the live data.")

    st.markdown(
        "The assistant can look up current weather and the upcoming Saturday/Sunday forecast for named "
        "locations. For example: *I want to take my kids hiking this weekend in Detroit. Which day is better? "
        "I don't like rain and ideally it should be above 60°F.*"
    )
    left, right = st.columns([3, 1])
    with left:
        # Streamlit retains keyed widget values between reruns. Upgrade only the old
        # stock value so a user's own in-progress question is never overwritten.
        if st.session_state.get("week4_prompt") == LEGACY_DEFAULT_PROMPT:
            st.session_state.week4_prompt = DEFAULT_PROMPT
        prompt = st.text_area(
            "Try a prompt",
            DEFAULT_PROMPT,
            key="week4_prompt",
            height=90,
        )
    with right:
        model = st.text_input("Model", os.getenv("OPENAI_MODEL", "gpt-4o-mini"), key="week4_model")
        run_with_tools = st.button("Run with tools", type="primary", use_container_width=True)
        run_without_tools = st.button("Run without tools", use_container_width=True)
    if run_with_tools or run_without_tools:
        if not os.getenv("OPENAI_API_KEY"):
            st.error("OPENAI_API_KEY is not configured.")
        elif not prompt.strip() or not model.strip():
            st.warning("Enter both a prompt and model.")
        else:
            try:
                use_tools = run_with_tools
                spinner_message = "Model deciding; runtime executing any requested tools…" if use_tools else "Running model without weather tools…"
                with st.spinner(spinner_message):
                    st.session_state.week4_result = run_direct_agent(prompt, model.strip(), use_tools=use_tools)
            except Exception as exc:
                st.error(f"Agent request failed: {type(exc).__name__}: {exc}")
    result = st.session_state.get("week4_result")
    if result:
        st.subheader("Final answer")
        st.caption(result.get("mode", "With tools"))
        st.write(result["answer"])
        count, latency = st.columns(2)
        count.metric("Tool calls", len(result["trace"]))
        latency.metric("Runtime latency", f"{result['latency']:.2f}s")
        with st.expander("Inspect runtime trace", expanded=True):
            if result["trace"]:
                st.json(result["trace"])
            else:
                st.info("No tool requested: this is the expected outcome for conceptual questions.")
    with st.expander("Tool schemas supplied to the model"):
        st.json([WEATHER_TOOL, WEEKEND_FORECAST_TOOL])

    st.divider()
    st.subheader("Benchmark results")
    st.caption(
        f"Run {len(LIVE_BENCHMARKS)} prompts against the selected model to measure tool selection and "
        "location arguments. This makes OpenAI and weather-provider requests."
    )
    if st.button("Run live benchmark", use_container_width=True):
        if not os.getenv("OPENAI_API_KEY"):
            st.error("OPENAI_API_KEY is not configured.")
        elif not model.strip():
            st.warning("Enter a model first.")
        else:
            try:
                with st.spinner(f"Running {len(LIVE_BENCHMARKS)} benchmark prompts…"):
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
