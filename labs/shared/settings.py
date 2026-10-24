"""Shared model settings and helpers used by every week's core logic."""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_MODEL = "gpt-5.4-mini"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_MAX_OUTPUT_TOKENS = 1000
# Standard, uncached $ per 1M tokens for the default model. Edit in the sidebar.
DEFAULT_INPUT_PRICE = 0.75
DEFAULT_OUTPUT_PRICE = 4.50


@dataclass(frozen=True)
class ModelSettings:
    """The model configuration every lab receives from the sidebar."""

    model: str = DEFAULT_MODEL
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS
    input_price: float = DEFAULT_INPUT_PRICE
    output_price: float = DEFAULT_OUTPUT_PRICE
    embedding_model: str = DEFAULT_EMBEDDING_MODEL

    def cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimated USD for one or more calls at the configured prices."""
        return (input_tokens * self.input_price + output_tokens * self.output_price) / 1_000_000


def has_api_key() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))
