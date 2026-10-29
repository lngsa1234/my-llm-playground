"""Weather connector: live Open-Meteo data, or the fake world.

Live mode reuses the Week 4 lab's Open-Meteo client (`labs/week4_tool_calling/weather.py`)
and normalizes its result to the fake tool's shape (`{"city", "temp_f", "conditions"}`)
so the model and Week 6 grading see the same keys either way. No credentials, no
approval: reading the weather has no side effects.
"""

from __future__ import annotations

from typing import Callable

from mini_muse import week4_tools
from mini_muse.connectors.base import ConnectorStatus, CredentialField, Mode


def _conditions(feels_like_f) -> str:
    """A short word for the sky, since Open-Meteo's current block has only temperatures."""
    try:
        f = float(feels_like_f)
    except (TypeError, ValueError):
        return "unknown"
    if f <= 32:
        return "freezing"
    if f <= 50:
        return "cold"
    if f <= 68:
        return "cool"
    if f <= 84:
        return "warm"
    return "hot"


def _live_get_weather(world, city):
    """Open-Meteo current weather, normalized to the fake get_weather shape. Never raises."""
    from labs.week4_tool_calling import weather as live

    try:
        data = live.get_weather(city)
    except Exception as exc:  # noqa: BLE001 - a live tool must never crash the agent loop
        return {"error": f"Weather service error: {exc}"}
    if "error" in data:
        return {"error": data["error"]}
    temp = data.get("temperature_f")
    place = ", ".join(p for p in (data.get("location"), data.get("state")) if p) or city
    return {"city": place, "temp_f": round(temp) if isinstance(temp, (int, float)) else temp,
            "feels_like_f": data.get("feels_like_f"), "conditions": _conditions(data.get("feels_like_f"))}


class WeatherConnector:
    name = "weather"
    title = "Weather (Open-Meteo)"
    tool_names = ["get_weather"]
    credentials: list[CredentialField] = []  # Open-Meteo needs no key

    def schemas(self) -> list[dict]:
        return [week4_tools.SCHEMAS[n] for n in self.tool_names]

    def functions(self, mode: Mode, creds: dict, *, world: dict) -> dict[str, Callable]:
        if mode == "live":
            return {"get_weather": _live_get_weather}
        return {"get_weather": week4_tools.get_weather}

    def readiness(self, mode: Mode, creds: dict) -> ConnectorStatus:
        if mode == "live":
            return ConnectorStatus(True, "Live Open-Meteo data (no key needed).")
        return ConnectorStatus(True, "Simulated weather from the fake world.")

    def risky_tools(self, mode: Mode) -> set[str]:
        return set()
