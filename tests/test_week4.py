from datetime import date
from unittest.mock import Mock, patch

from core.week4 import get_weekend_forecast, system_prompt, upcoming_weekend


def test_upcoming_weekend_is_the_next_saturday_and_sunday():
    assert upcoming_weekend(date(2026, 10, 12)) == (date(2026, 10, 17), date(2026, 10, 18))
    assert upcoming_weekend(date(2026, 10, 17)) == (date(2026, 10, 17), date(2026, 10, 18))


def test_relative_weekend_prompt_does_not_request_dates():
    prompt = system_prompt(date(2026, 10, 12))
    assert "this weekend' means Saturday, October 17 and Sunday, October 18" in prompt
    assert "ask only for the location" in prompt
    assert "Do not ask for dates" in prompt


@patch("core.week4.requests.get")
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
