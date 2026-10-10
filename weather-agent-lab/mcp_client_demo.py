"""Discover weather tools over MCP, then let an LLM use them.

Run: python mcp_client_demo.py "Which is warmer right now, Detroit or Miami?"
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import OpenAI


MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
SYSTEM_PROMPT = (
    "You are a concise weather assistant. Use a tool only for current weather "
    "in a named location. Never invent weather values; accurately communicate "
    "tool errors. Use one lookup per city when comparing cities."
)


def as_openai_tools(mcp_tools: list[Any]) -> list[dict[str, Any]]:
    """Translate MCP's discovered tool definitions into OpenAI tool schemas."""
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.inputSchema,
            },
        }
        for tool in mcp_tools
    ]


def tool_result_as_text(result: Any) -> str:
    """Keep the MCP result intact for the model, including error information."""
    if getattr(result, "structuredContent", None) is not None:
        return json.dumps(result.structuredContent)
    parts = [getattr(item, "text", str(item)) for item in result.content]
    return "\n".join(parts)


async def run_assistant(prompt: str) -> str:
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is missing. Add it to .env first.")

    server_file = Path(__file__).with_name("weather_mcp_server.py")
    server = StdioServerParameters(command=sys.executable, args=[str(server_file)])
    client = OpenAI()

    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            discovered = await session.list_tools()
            tools = as_openai_tools(discovered.tools)
            print("Discovered MCP tools:", ", ".join(tool.name for tool in discovered.tools))

            messages: list[dict[str, Any]] = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
            for _ in range(5):
                response = client.chat.completions.create(
                    model=MODEL, messages=messages, tools=tools, tool_choice="auto"
                )
                assistant_message = response.choices[0].message
                messages.append(assistant_message.model_dump(exclude_none=True))
                if not assistant_message.tool_calls:
                    return assistant_message.content or "I couldn't generate a response."

                for call in assistant_message.tool_calls:
                    try:
                        arguments = json.loads(call.function.arguments)
                    except json.JSONDecodeError:
                        arguments = {}
                    result = await session.call_tool(call.function.name, arguments=arguments)
                    result_text = tool_result_as_text(result)
                    print(f"MCP call: {call.function.name}({call.function.arguments})")
                    print(f"MCP result: {result_text}")
                    messages.append(
                        {"role": "tool", "tool_call_id": call.id, "content": result_text}
                    )
    return "I couldn't complete the request because the tool-call limit was reached."


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or input("Ask a weather question: ")
    try:
        print("\nAssistant:", asyncio.run(run_assistant(question)))
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
