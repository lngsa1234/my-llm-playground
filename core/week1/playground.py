"""Week 1 core logic: one independent LLM API call, with optional structured output."""

from __future__ import annotations

import keyword
import time

from openai import OpenAI
from pydantic import create_model

from core.common import ModelSettings

SUPPORTED_TYPES = {"str": str, "int": int, "float": float, "bool": bool, "list[str]": list[str]}


def build_output_model(schema_text: str):
    """Build a small Pydantic schema from editable `name: type` fields."""
    fields = {}
    for raw_line in schema_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if ":" not in line:
            raise ValueError(f"Use `name: type` for every field: {line}")
        name, type_name = (part.strip() for part in line.split(":", 1))
        if not name.isidentifier() or keyword.iskeyword(name) or name.startswith("_"):
            raise ValueError(f"Invalid field name: {name}")
        if type_name not in SUPPORTED_TYPES:
            raise ValueError(f"Unsupported type: {type_name}")
        if name in fields:
            raise ValueError(f"Duplicate field: {name}")
        fields[name] = (SUPPORTED_TYPES[type_name], ...)
    if not fields:
        raise ValueError("Define at least one JSON field.")
    return create_model("Week1Output", **fields)


def run_single_call(settings: ModelSettings, instructions: str, prompt: str, schema_text: str | None = None) -> dict:
    """Make one API call and return the answer with token use, latency and cost."""
    client = OpenAI()
    start = time.perf_counter()
    if schema_text is not None:
        response = client.responses.parse(
            model=settings.model, instructions=instructions, input=prompt,
            text_format=build_output_model(schema_text), max_output_tokens=settings.max_output_tokens,
        )
        answer = response.output_parsed.model_dump() if response.output_parsed else None
    else:
        response = client.responses.create(
            model=settings.model, instructions=instructions, input=prompt,
            max_output_tokens=settings.max_output_tokens,
        )
        answer = response.output_text
    usage = response.usage
    return {
        "answer": answer,
        "structured": schema_text is not None,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "total_tokens": usage.total_tokens,
        "latency": time.perf_counter() - start,
        "cost": settings.cost(usage.input_tokens, usage.output_tokens),
        "status": response.status,
    }
