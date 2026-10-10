"""Direct OpenAI tool-calling weather assistant.

Run: python tool_calling_demo.py "What's the weather in Detroit?"
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from weather_tool import get_weather


MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
SYSTEM_PROMPT = (
    "You are a concise weather assistant. Use get_weather only when the user "
    "asks for current weather for a specific location. For a comparison, call "
    "the tool once per location. Never invent weather data. If the tool returns "
    "an error, clearly tell the user and do not make up a temperature."
)

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


def run_assistant(prompt: str) -> str:
    """Run the agent execution loop and return its final answer."""
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is missing. Add it to .env first.")

    client = OpenAI()
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    # A loop is essential: a model may request one or several tools, then may
    # request more tools after seeing results.
    for _ in range(5):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=[WEATHER_TOOL],
            tool_choice="auto",
        )
        assistant_message = response.choices[0].message
        messages.append(assistant_message.model_dump(exclude_none=True))

        if not assistant_message.tool_calls:
            return assistant_message.content or "I couldn't generate a response."

        for tool_call in assistant_message.tool_calls:
            if tool_call.function.name != "get_weather":
                result: dict[str, Any] = {"error": "Unsupported tool requested."}
            else:
                try:
                    arguments = json.loads(tool_call.function.arguments)
                    result = get_weather(arguments["location"])
                except (json.JSONDecodeError, KeyError, TypeError):
                    result = {"error": "The weather request had invalid arguments."}

            print(f"Tool call: {tool_call.function.name}({tool_call.function.arguments})")
            print(f"Tool result: {json.dumps(result)}")
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result),
                }
            )

    return "I couldn't complete the request because the tool-call limit was reached."


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or input("Ask a weather question: ")
    try:
        print("\nAssistant:", run_assistant(question))
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
