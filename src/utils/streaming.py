"""
Streaming Utilities

Provides streaming support for long-running operations using
Anthropic SDK's streaming pattern (messages.stream).

When users are waiting for dependency analysis across large repositories,
streaming gives real-time feedback instead of silent waiting.

Based on the Anthropic SDK's tools_stream.py and messages_stream.py examples.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Callable, Optional

import anthropic


def stream_with_tools(
    prompt: str,
    tools: list[dict[str, Any]],
    *,
    model: str | None = None,
    system: str | None = None,
    max_tokens: int = 4096,
    on_text: Callable[[str], None] | None = None,
    on_tool_use: Callable[[str, dict], None] | None = None,
) -> anthropic.types.Message:
    """
    Stream a Claude response with tool use support.

    Provides real-time text output and tool call notifications during
    long-running agent operations.

    Args:
        prompt: User message
        tools: List of tool definitions (Anthropic format)
        model: Model name (defaults to LLM_MODEL_NAME env var)
        system: Optional system prompt
        max_tokens: Max tokens for response
        on_text: Callback for each text delta (default: print to stdout)
        on_tool_use: Callback when a tool call is detected (name, input)

    Returns:
        The complete Message object after streaming finishes

    Example:
        message = stream_with_tools(
            prompt="Analyze dependencies for ...",
            tools=[...],
            on_text=lambda t: print(t, end="", flush=True),
            on_tool_use=lambda name, inp: print(f"\\nCalling {name}..."),
        )
    """
    client = anthropic.Anthropic()
    model = model or os.getenv("LLM_MODEL_NAME", "claude-sonnet-4-5-20250929")

    if on_text is None:
        on_text = lambda t: print(t, end="", flush=True)

    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
        "tools": tools,
    }
    if system:
        kwargs["system"] = system

    with client.messages.stream(**kwargs) as stream:
        for event in stream:
            if event.type == "content_block_delta":
                if hasattr(event.delta, "text"):
                    on_text(event.delta.text)
            elif event.type == "content_block_start":
                if hasattr(event.content_block, "name") and on_tool_use:
                    on_tool_use(event.content_block.name, {})

        return stream.get_final_message()


def print_streaming_progress(
    step: str,
    detail: str = "",
    *,
    emoji: str = "⏳",
    file: Any = None,
) -> None:
    """
    Print a progress update during streaming operations.

    Args:
        step: Current step description
        detail: Optional detail text
        emoji: Emoji prefix
        file: Output file (default: sys.stderr for non-interfering output)
    """
    out = file or sys.stderr
    msg = f"{emoji} {step}"
    if detail:
        msg += f" — {detail}"
    print(msg, file=out, flush=True)
