"""MCP stdio server exposing the lab's weather tools from weather.py.

Run directly only for debugging: python labs/week4_tool_calling/weather_mcp_server.py
Normally mcp_client_demo.py starts this process for you.
"""

from mcp.server.fastmcp import FastMCP

from weather import get_weather, get_weekend_forecast

mcp = FastMCP("weather-server")


@mcp.tool(name="get_weather")
def current_weather(location: str) -> dict:
    """Get current weather for a city or location, including Fahrenheit temperatures."""
    return get_weather(location)


@mcp.tool(name="get_weekend_forecast")
def weekend_forecast(location: str) -> dict:
    """Get the daily forecast for the upcoming Saturday and Sunday in a named location."""
    return get_weekend_forecast(location)


if __name__ == "__main__":
    mcp.run(transport="stdio")
