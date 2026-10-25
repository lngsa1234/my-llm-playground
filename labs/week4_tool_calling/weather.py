"""Week 4 core logic: weather tools and a tool-calling agent loop, using live Open-Meteo data.

This one module is shared by the web page (page.py), the command-line demo
(tool_calling_demo.py) and the MCP server (weather_mcp_server.py).

Try the tools on their own, with no LLM involved:
    python labs/week4_tool_calling/weather.py Detroit
"""

from __future__ import annotations

import json
import time
from datetime import date, timedelta
from typing import Any

import requests
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


def run_direct_agent(prompt: str, model: str, use_tools: bool = True, max_tool_rounds: int = 5,
                     max_output_tokens: int | None = None, tools: list[str] | None = None) -> dict[str, Any]:
    """Run the agent with optional weather tools and retain its trace for the lab UI.

    tools: names of the tools to offer (default: both). The result also counts model calls and tokens.
    """
    offered = [t for t in (WEATHER_TOOL, WEEKEND_FORECAST_TOOL) if tools is None or t["function"]["name"] in tools]
    use_tools = use_tools and bool(offered)
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
    calls: list[dict[str, Any]] = []  # one entry per model call: what was sent, tokens, what came back
    usage = {"model_calls": 0, "input_tokens": 0, "output_tokens": 0}
    start = time.perf_counter()

    def finish(answer: str) -> dict[str, Any]:
        return {"answer": answer, "trace": trace, "calls": calls, "latency": time.perf_counter() - start,
                "mode": "With tools" if use_tools else "Without tools", **usage}

    for round_number in range(1, max_tool_rounds + 1):
        request: dict[str, Any] = {"model": model, "messages": messages}
        if max_output_tokens:
            request["max_completion_tokens"] = max_output_tokens
        if use_tools:
            request.update({"tools": offered, "tool_choice": "auto"})
        sent = json.loads(json.dumps(messages, default=str))  # a snapshot: the list keeps growing
        sent_request = json.loads(json.dumps(request, default=str))  # the whole body: messages + tools
        call_started = time.perf_counter()
        response = OpenAI().chat.completions.create(**request)
        usage["model_calls"] += 1
        tokens_in = getattr(getattr(response, "usage", None), "prompt_tokens", 0)
        tokens_out = getattr(getattr(response, "usage", None), "completion_tokens", 0)
        usage["input_tokens"] += tokens_in if isinstance(tokens_in, int) else 0
        usage["output_tokens"] += tokens_out if isinstance(tokens_out, int) else 0
        assistant_message = response.choices[0].message
        requested = [{"tool": c.function.name, "arguments": c.function.arguments} for c in (assistant_message.tool_calls or [])]
        calls.append({"call": round_number, "messages": sent, "request": sent_request,
                      "tools": [t["function"]["name"] for t in offered] if use_tools else [],
                      "input_tokens": tokens_in if isinstance(tokens_in, int) else 0,
                      "output_tokens": tokens_out if isinstance(tokens_out, int) else 0,
                      "seconds": time.perf_counter() - call_started,
                      "returned": {"tool_calls": requested} if requested else {"answer": assistant_message.content or ""}})
        messages.append(assistant_message.model_dump(exclude_none=True))
        if not assistant_message.tool_calls:
            return finish(assistant_message.content or "No visible answer was returned.")
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
            trace.append({"tool": call.function.name, "arguments": call.function.arguments, "result": result,
                          "round": round_number})
            messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)})
    return finish(f"Stopped: the model was still asking for tools after {max_tool_rounds} rounds.")


LIVE_BENCHMARKS = [
    {
        "prompt": "I'm deciding whether to take my toddler to the Detroit Zoo this afternoon. Is the current temperature or feels-like temperature jacket weather?",
        "calls": [{"tool": "get_weather", "location": "Detroit"}],
    },
    {
        "prompt": "My parents are leaving Miami and landing in Chicago tonight. Which place feels warmer right now, and by how many degrees?",
        "calls": [
            {"tool": "get_weather", "location": "Miami"},
            {"tool": "get_weather", "location": "Chicago"},
        ],
    },
    {
        "prompt": "Compare current conditions in Portland, Oregon and Portland, Maine. Keep the two cities distinct and use feels-like temperature for the recommendation.",
        "calls": [
            {"tool": "get_weather", "location": "Portland, Oregon"},
            {"tool": "get_weather", "location": "Portland, Maine"},
        ],
    },
    {
        "prompt": "For an outdoor family hike in Detroit this weekend, which day is the safer choice if rain is a deal-breaker and we prefer a high above 60°F?",
        "calls": [{"tool": "get_weekend_forecast", "location": "Detroit"}],
    },
    {
        "prompt": "We can drive either to Ann Arbor or Lansing this weekend. Which destination/day combination gives us the best chance of a dry picnic with a high over 65°F?",
        "calls": [
            {"tool": "get_weekend_forecast", "location": "Ann Arbor"},
            {"tool": "get_weekend_forecast", "location": "Lansing"},
        ],
    },
    {
        "prompt": "I'm photographing fall color near Washington, DC this weekend. Compare Saturday and Sunday for rain risk and daytime high; do not assume that 'Washington' means Washington state.",
        "calls": [{"tool": "get_weekend_forecast", "location": "Washington DC"}],
    },
    {
        "prompt": "Before I book a Sunday beach outing in San Diego, tell me whether Saturday or Sunday is less likely to be wet. Also flag it if neither day reaches 70°F.",
        "calls": [{"tool": "get_weekend_forecast", "location": "San Diego"}],
    },
    {
        "prompt": "I leave Boston now and arrive in Phoenix tomorrow. Give me the current conditions in Boston, then compare Phoenix's upcoming-weekend days for a hot, dry walk.",
        "calls": [
            {"tool": "get_weather", "location": "Boston"},
            {"tool": "get_weekend_forecast", "location": "Phoenix"},
        ],
    },
    {
        "prompt": "What are the current conditions in São Paulo, Brazil and Reykjavík, Iceland? I care more about feels-like temperature than the actual temperature.",
        "calls": [
            {"tool": "get_weather", "location": "São Paulo, Brazil"},
            {"tool": "get_weather", "location": "Reykjavík, Iceland"},
        ],
    },
    {
        "prompt": "Do not look up weather. Explain, in general terms, why coastal and inland cities can have different temperatures.",
        "calls": [],
    },
    {
        "prompt": "The place name may be invalid: what is the current weather in asdfghxyz? Report a lookup problem honestly if it cannot be found.",
        "calls": [{"tool": "get_weather", "location": "asdfghxyz"}],
    },
]


def run_live_benchmark(model: str, max_tool_rounds: int = 5, max_output_tokens: int | None = None,
                       tools: list[str] | None = None, progress=None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Score a small live set for tool selection and location arguments."""
    rows: list[dict[str, Any]] = []
    details: list[dict[str, Any]] = []
    for number, case in enumerate(LIVE_BENCHMARKS, start=1):
        result = run_direct_agent(case["prompt"], model, max_tool_rounds=max_tool_rounds,
                                  max_output_tokens=max_output_tokens, tools=tools)
        actual_calls = []
        for entry in result["trace"]:
            try:
                actual_calls.append({"tool": entry["tool"], "location": json.loads(entry["arguments"])["location"]})
            except (json.JSONDecodeError, KeyError, TypeError):
                actual_calls.append({"tool": entry["tool"], "location": "<invalid arguments>"})
        expected_calls = case["calls"]
        selection_passed = [call["tool"] for call in actual_calls] == [call["tool"] for call in expected_calls]
        actual_locations = [call["location"] for call in actual_calls]
        expected_locations = [call["location"] for call in expected_calls]
        canonical_actual = [LOCATION_ALIASES.get(item.casefold(), item).casefold() for item in actual_locations]
        canonical_expected = [LOCATION_ALIASES.get(item.casefold(), item).casefold() for item in expected_locations]
        arguments_passed = canonical_actual == canonical_expected
        rows.append(
            {
                "Prompt": case["prompt"],
                "Expected calls": len(expected_calls),
                "Actual calls": len(actual_calls),
                "Tool selection": "PASS" if selection_passed else "FAIL",
                "Arguments": "PASS" if arguments_passed else "FAIL",
                "Expected": "; ".join(f"{c['tool']}({c['location']})" for c in expected_calls) or "no tool",
                "Actual": "; ".join(f"{c['tool']}({c['location']})" for c in actual_calls) or "no tool",
            }
        )
        details.append({"prompt": case["prompt"], **result})
        if progress:
            progress(number, len(LIVE_BENCHMARKS))
    return rows, details


TOOL_FUNCTIONS = {"get_weather": get_weather, "get_weekend_forecast": get_weekend_forecast}


if __name__ == "__main__":
    import sys

    place = " ".join(sys.argv[1:]) or "Detroit"
    print("get_weather:", json.dumps(get_weather(place), indent=2))
    print("get_weekend_forecast:", json.dumps(get_weekend_forecast(place), indent=2))
