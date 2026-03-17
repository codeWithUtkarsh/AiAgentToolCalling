"""
Structured Output Parsing Utilities

Uses Anthropic SDK's messages.parse() pattern for type-safe AI responses.
Instead of regex-extracting JSON from free-text LLM responses, we get
validated Pydantic models directly.

Example:
    from src.models.parsing import parse_structured
    from src.models.schemas import ErrorAnalysis

    result = parse_structured(
        ErrorAnalysis,
        prompt="Analyze this error...",
        model="claude-sonnet-4-5-20250929",
    )
    print(result.suspected_package)  # typed, validated
"""

from __future__ import annotations

import os
from typing import Type, TypeVar

import anthropic
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    """Get or create a singleton Anthropic client."""
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def parse_structured(
    output_type: Type[T],
    prompt: str,
    *,
    model: str | None = None,
    system: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0,
) -> T:
    """
    Parse a structured response from Claude using Anthropic SDK's messages.parse().

    This replaces the pattern of:
    1. Asking Claude to output JSON
    2. Regex-extracting JSON from the response
    3. Manually parsing with json.loads()

    Args:
        output_type: Pydantic model class to parse into
        prompt: User prompt
        model: Model name (defaults to LLM_MODEL_NAME env var)
        system: Optional system prompt
        max_tokens: Max tokens for response
        temperature: Temperature (0 = deterministic)

    Returns:
        Validated Pydantic model instance
    """
    client = _get_client()
    model = model or os.getenv("LLM_MODEL_NAME", "claude-sonnet-4-5-20250929")

    messages = [{"role": "user", "content": prompt}]

    kwargs: dict = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "output_format": output_type,
    }

    if system:
        kwargs["system"] = system

    response = client.messages.parse(**kwargs)
    return response.parsed_output
