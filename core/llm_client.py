"""Small OpenAI adapter so API work stays outside the Streamlit UI."""

from __future__ import annotations

import json
import time

from openai import OpenAI


def execute_goal_call(model: str, context: dict, operation: str, output_tokens: int) -> dict:
    instructions = (
        "You are a careful product and systems design assistant. Use only the supplied "
        "context; label uncertainty instead of inventing facts. Approved requirements and "
        "decisions override earlier conversation. Return a useful, clearly structured Markdown "
        f"artifact for this workflow operation: {operation}."
    )
    start = time.perf_counter()
    response = OpenAI().responses.create(
        model=model,
        instructions=instructions,
        input=json.dumps(context, indent=2),
        max_output_tokens=output_tokens,
    )
    usage = response.usage
    return {
        "text": response.output_text,
        "latency_seconds": time.perf_counter() - start,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "total_tokens": usage.total_tokens,
        "status": response.status,
    }
