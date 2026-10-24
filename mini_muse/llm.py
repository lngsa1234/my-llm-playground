"""A thin wrapper around the OpenAI API that every Mini Muse component uses.

It does three things and nothing clever:
  parse()  one call that must return a Pydantic object (structured output, Week 1)
  chat()   one chat call, optionally offering tools (Weeks 2, 4, 5)
  embed()  embeddings for semantic search (Week 3)

and keeps a running total of calls, tokens and cost, so every screen can show
what a step cost. Tests pass a fake object with the same three methods.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from labs.shared.settings import ModelSettings


@dataclass
class Usage:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    def add(self, input_tokens: int, output_tokens: int) -> None:
        self.calls += 1
        self.input_tokens += input_tokens or 0
        self.output_tokens += output_tokens or 0


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str  # raw JSON text, exactly as the model wrote it


@dataclass
class Reply:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)

    def as_message(self) -> dict:
        """The assistant message to append to the conversation before tool results."""
        message: dict[str, Any] = {"role": "assistant", "content": self.content or ""}
        if self.tool_calls:
            message["tool_calls"] = [
                {"id": c.id, "type": "function", "function": {"name": c.name, "arguments": c.arguments}}
                for c in self.tool_calls
            ]
        return message


class LLM:
    def __init__(self, settings: ModelSettings, client=None):
        if client is None:
            from openai import OpenAI

            client = OpenAI()
        self.client = client
        self.settings = settings
        self.usage = Usage()

    @property
    def model(self) -> str:
        return self.settings.model

    def cost(self) -> float:
        return self.settings.cost(self.usage.input_tokens, self.usage.output_tokens)

    def parse(self, instructions: str, text: str, schema):
        response = self.client.responses.parse(
            model=self.settings.model, instructions=instructions, input=text, text_format=schema,
            max_output_tokens=self.settings.max_output_tokens)
        self.usage.add(response.usage.input_tokens, response.usage.output_tokens)
        if response.output_parsed is None:
            raise ValueError("The model did not return the requested structure.")
        return response.output_parsed

    def chat(self, messages: list[dict], tools: list[dict] | None = None, model: str | None = None) -> Reply:
        request: dict[str, Any] = {"model": model or self.settings.model, "messages": messages,
                                   "max_completion_tokens": self.settings.max_output_tokens}
        if tools:
            request.update({"tools": tools, "tool_choice": "auto"})
        response = self.client.chat.completions.create(**request)
        if response.usage:
            self.usage.add(response.usage.prompt_tokens, response.usage.completion_tokens)
        message = response.choices[0].message
        calls = [ToolCall(c.id, c.function.name, c.function.arguments or "{}") for c in (message.tool_calls or [])]
        return Reply(content=message.content or "", tool_calls=calls)

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self.client.embeddings.create(model=self.settings.embedding_model, input=texts)
        self.usage.add(response.usage.prompt_tokens, 0)
        return [item.embedding for item in response.data]


def parse_arguments(raw: str) -> tuple[dict, str | None]:
    """Decode a tool call's JSON arguments. Models sometimes write invalid JSON."""
    try:
        args = json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        return {}, f"Arguments were not valid JSON ({exc.msg}). Call the tool again with valid JSON."
    if not isinstance(args, dict):
        return {}, "Arguments must be a JSON object."
    return args, None


def cli_llm() -> "LLM":
    """The model for command-line runs: reads .env, exits with a clear message if the key is missing."""
    import os

    from dotenv import load_dotenv

    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not set. Copy .env.example to .env and add your key.")
    return LLM(ModelSettings(model=os.getenv("OPENAI_MODEL") or ModelSettings().model))
