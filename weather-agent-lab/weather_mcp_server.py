"""MCP stdio server exposing the shared weather capability.

Run directly only for debugging: python weather_mcp_server.py
Normally mcp_client_demo.py starts this process for you.
"""

from mcp.server.fastmcp import FastMCP

from weather_tool import get_weather


mcp = FastMCP("weather-server")


@mcp.tool(name="get_weather")
def weather(location: str) -> dict:
    """Get current weather for a city or location, including Fahrenheit temperatures."""
    return get_weather(location)


if __name__ == "__main__":
    mcp.run(transport="stdio")
