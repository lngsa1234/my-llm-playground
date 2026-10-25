from datetime import date
from unittest.mock import Mock, patch

import labs.week4_tool_calling.weather as week4
from labs.week4_tool_calling.weather import get_weekend_forecast, run_direct_agent, system_prompt, upcoming_weekend


def test_upcoming_weekend_is_the_next_saturday_and_sunday():
    assert upcoming_weekend(date(2026, 10, 12)) == (date(2026, 10, 17), date(2026, 10, 18))
    assert upcoming_weekend(date(2026, 10, 17)) == (date(2026, 10, 17), date(2026, 10, 18))


def test_relative_weekend_prompt_does_not_request_dates():
    prompt = system_prompt(date(2026, 10, 12))
    assert "this weekend' means Saturday, October 17 and Sunday, October 18" in prompt
    assert "ask only for the location" in prompt
    assert "Do not ask for dates" in prompt


@patch("labs.week4_tool_calling.weather.requests.get")
def test_weekend_forecast_returns_both_days(mock_get):
    geocode = Mock()
    geocode.raise_for_status.return_value = None
    geocode.json.return_value = {
        "results": [{"name": "Detroit", "admin1": "Michigan", "country": "United States", "latitude": 42.3, "longitude": -83.0}]
    }
    forecast = Mock()
    forecast.raise_for_status.return_value = None
    forecast.json.return_value = {
        "daily": {
            "time": ["2026-10-17", "2026-10-18"],
            "temperature_2m_max": [65.0, 58.0],
            "temperature_2m_min": [48.0, 44.0],
            "precipitation_probability_max": [10, 70],
            "precipitation_sum": [0.0, 8.0],
        }
    }
    mock_get.side_effect = [geocode, forecast]

    result = get_weekend_forecast("Detroit", today=date(2026, 10, 12))

    assert result["location"] == "Detroit"
    assert result["forecast"] == [
        {
            "date": "2026-10-17",
            "day": "Saturday",
            "high_f": 65.0,
            "low_f": 48.0,
            "precipitation_probability_max": 10,
            "precipitation_sum_in": 0.0,
        },
        {
            "date": "2026-10-18",
            "day": "Sunday",
            "high_f": 58.0,
            "low_f": 44.0,
            "precipitation_probability_max": 70,
            "precipitation_sum_in": 8.0 / 25.4,
        },
    ]
    assert mock_get.call_args_list[1].kwargs["params"]["forecast_days"] == 16


@patch("labs.week4_tool_calling.weather.OpenAI")
def test_run_without_tools_omits_tool_schema(mock_openai):
    response = Mock()
    response.choices = [Mock()]
    response.choices[0].message.content = "I need live forecast data to compare the days."
    response.choices[0].message.tool_calls = []
    response.choices[0].message.model_dump.return_value = {"role": "assistant", "content": response.choices[0].message.content}
    create = mock_openai.return_value.chat.completions.create
    create.return_value = response

    result = run_direct_agent("Which hiking day is better in Detroit?", "test-model", use_tools=False)

    assert result["mode"] == "Without tools"
    assert result["trace"] == []
    request = create.call_args.kwargs
    assert "tools" not in request
    assert "without access to live weather data" in request["messages"][0]["content"]


def test_live_benchmark_scores_the_expected_tool_and_location(monkeypatch):
    monkeypatch.setattr(
        week4,
        "LIVE_BENCHMARKS",
        [{"prompt": "Weekend hike", "calls": [{"tool": "get_weekend_forecast", "location": "Detroit"}]}],
    )
    monkeypatch.setattr(
        week4,
        "run_direct_agent",
        lambda *_, **__: {"answer": "Saturday", "latency": 0.1, "trace": [{"tool": "get_weekend_forecast", "arguments": '{"location": "Detroit"}', "result": {}}]},
    )

    rows, _ = week4.run_live_benchmark("test-model")

    assert rows == [{"Prompt": "Weekend hike", "Expected calls": 1, "Actual calls": 1, "Tool selection": "PASS", "Arguments": "PASS",
                     "Expected": "get_weekend_forecast(Detroit)", "Actual": "get_weekend_forecast(Detroit)"}]


@patch("labs.week4_tool_calling.weather.OpenAI")
def test_agent_counts_tokens_records_rounds_and_offers_only_chosen_tools(mock_openai):
    from types import SimpleNamespace

    def message(content=None, calls=None):
        m = Mock()
        m.content, m.tool_calls = content, calls or []
        m.model_dump.return_value = {"role": "assistant", "content": content}
        return SimpleNamespace(choices=[SimpleNamespace(message=m)],
                               usage=SimpleNamespace(prompt_tokens=100, completion_tokens=20))

    call = SimpleNamespace(id="c1", function=SimpleNamespace(name="get_weather", arguments='{"location": "Detroit"}'))
    create = mock_openai.return_value.chat.completions.create
    create.side_effect = [message(calls=[call]), message("48°F in Detroit.")]
    with patch.object(week4, "get_weather", return_value={"temperature_f": 48}):
        result = run_direct_agent("Weather in Detroit?", "m", tools=["get_weather"])
    assert result["model_calls"] == 2 and result["input_tokens"] == 200 and result["output_tokens"] == 40
    assert result["trace"][0]["round"] == 1
    first, second = result["calls"]
    assert [m["role"] for m in first["messages"]] == ["system", "user"]
    assert first["returned"] == {"tool_calls": [{"tool": "get_weather", "arguments": '{"location": "Detroit"}'}]}
    assert [m["role"] for m in second["messages"]][-1] == "tool" and second["returned"] == {"answer": "48°F in Detroit."}
    assert first["input_tokens"] == 100 and first["tools"] == ["get_weather"]
    assert [t["function"]["name"] for t in first["request"]["tools"]] == ["get_weather"]
    assert first["request"]["messages"] == first["messages"] and first["request"]["tool_choice"] == "auto"
    assert second["response"]["message"]["content"] == "48°F in Detroit." and first["response"]["usage"]["prompt_tokens"] == 100
    assert [t["function"]["name"] for t in create.call_args_list[0].kwargs["tools"]] == ["get_weather"]
    create.side_effect = [message("I can't check live weather.")]
    no_tools = run_direct_agent("Weather in Detroit?", "m", tools=[])
    assert no_tools["mode"] == "Without tools" and "tools" not in create.call_args.kwargs
