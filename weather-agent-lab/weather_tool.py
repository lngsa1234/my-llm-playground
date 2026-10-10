"""Weather capability used by both the direct and MCP examples.

Open-Meteo does not require an API key.  This module deliberately contains no
LLM code: it is an ordinary, independently testable integration.
"""

from __future__ import annotations

from typing import Any

import requests


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT_SECONDS = 10
LOCATION_ALIASES = {
    "washington dc": "Washington, D.C.",
    "washington, dc": "Washington, D.C.",
    "washington d.c.": "Washington, D.C.",
    "washington, d.c.": "Washington, D.C.",
}


def _error(message: str) -> dict[str, str]:
    """Return errors in the same JSON-friendly shape as successful results."""
    return {"error": message}


def get_weather(location: str) -> dict[str, Any]:
    """Get the current Fahrenheit temperature and apparent temperature.

    ``location`` may be a city, region, or other place understood by
    Open-Meteo's geocoder.  Network and provider errors are returned as data
    rather than raised so an agent can accurately explain what went wrong.
    """
    location = location.strip()
    if not location:
        return _error("Location is required.")
    lookup_location = LOCATION_ALIASES.get(location.casefold(), location)

    try:
        geocode_response = requests.get(
            GEOCODING_URL,
            params={"name": lookup_location, "count": 1, "language": "en", "format": "json"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        geocode_response.raise_for_status()
        results = geocode_response.json().get("results", [])
    except (requests.RequestException, ValueError):
        return _error("Weather service is temporarily unavailable.")

    if not results:
        return _error("Location not found.")

    place = results[0]
    try:
        weather_response = requests.get(
            FORECAST_URL,
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": "temperature_2m,apparent_temperature",
                "temperature_unit": "fahrenheit",
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        weather_response.raise_for_status()
        current = weather_response.json()["current"]
        return {
            "location": place["name"],
            "state": place.get("admin1"),
            "country": place.get("country"),
            "temperature_f": current["temperature_2m"],
            "feels_like_f": current["apparent_temperature"],
        }
    except (KeyError, requests.RequestException, ValueError):
        return _error("Weather service is temporarily unavailable.")


if __name__ == "__main__":
    import json

    print(json.dumps(get_weather("Detroit"), indent=2))
