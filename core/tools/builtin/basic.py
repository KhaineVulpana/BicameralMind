"""Basic built-in tools."""

from __future__ import annotations

from datetime import datetime
from typing import Dict

from ..models import ToolDefinition, ToolProvider


def echo(text: str) -> str:
    return text


def timestamp() -> str:
    return datetime.utcnow().isoformat() + "Z"


def json_keys(payload: Dict) -> list[str]:
    return list(payload.keys())


TOOL_DEFINITIONS = [
    ToolDefinition(
        name="local.echo",
        description="Echo back the provided text.",
        provider=ToolProvider.LOCAL,
        input_schema={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
        output_schema={"type": "string"},
        tags=["local", "utility"],
        config={"entrypoint": "core.tools.builtin.basic:echo"},
    ),
    ToolDefinition(
        name="local.timestamp",
        description="Return current UTC timestamp.",
        provider=ToolProvider.LOCAL,
        input_schema={"type": "object", "properties": {}},
        output_schema={"type": "string"},
        tags=["local", "utility", "time"],
        config={"entrypoint": "core.tools.builtin.basic:timestamp"},
    ),
    ToolDefinition(
        name="local.json_keys",
        description="Return top-level keys from a JSON object.",
        provider=ToolProvider.LOCAL,
        input_schema={
            "type": "object",
            "properties": {"payload": {"type": "object"}},
            "required": ["payload"],
        },
        output_schema={"type": "array"},
        tags=["local", "utility", "json"],
        config={"entrypoint": "core.tools.builtin.basic:json_keys"},
    ),
]


TOOL_CALLABLES = {
    "local.echo": echo,
    "local.timestamp": timestamp,
    "local.json_keys": json_keys,
}
