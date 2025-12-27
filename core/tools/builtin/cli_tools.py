"""Built-in CLI tools for local automation.

These are intentionally small primitives for doing real work from the UI/tool API.
"""

from __future__ import annotations

from ..models import ToolDefinition, ToolProvider


TOOL_DEFINITIONS = [
    ToolDefinition(
        name="cli.powershell",
        description="Run a PowerShell script and return stdout/stderr.",
        provider=ToolProvider.CLI,
        input_schema={
            "type": "object",
            "properties": {"script": {"type": "string"}},
            "required": ["script"],
        },
        output_schema={"type": "string"},
        tags=["cli", "powershell", "system"],
        risk="high",
        config={
            "command": "powershell",
            "args": ["-NoProfile", "-NonInteractive", "-Command", "{script}"],
            "cwd": ".",
        },
    ),
    ToolDefinition(
        name="cli.git",
        description="Run git with args (e.g. ['status'] or ['diff', '--stat']).",
        provider=ToolProvider.CLI,
        input_schema={
            "type": "object",
            "properties": {"args": {"type": "array", "items": {"type": "string"}}},
            "required": ["args"],
        },
        output_schema={"type": "string"},
        tags=["cli", "git", "vcs"],
        risk="medium",
        config={
            "command": "git",
            "args_param": "args",
            "cwd": ".",
        },
    ),
    ToolDefinition(
        name="cli.py",
        description="Run Python via the 'py' launcher with args (e.g. ['-m','pip','--version']).",
        provider=ToolProvider.CLI,
        input_schema={
            "type": "object",
            "properties": {"args": {"type": "array", "items": {"type": "string"}}},
            "required": ["args"],
        },
        output_schema={"type": "string"},
        tags=["cli", "python"],
        risk="high",
        config={
            "command": "py",
            "args_param": "args",
            "cwd": ".",
        },
    ),
    ToolDefinition(
        name="cli.rg",
        description="Run ripgrep in the repo (returns matches or empty output).",
        provider=ToolProvider.CLI,
        input_schema={
            "type": "object",
            "properties": {"args": {"type": "array", "items": {"type": "string"}}},
            "required": ["args"],
        },
        output_schema={"type": "string"},
        tags=["cli", "search", "ripgrep"],
        risk="low",
        config={
            "command": "rg",
            "args_param": "args",
            # rg returns exit code 1 when there are no matches (not an error for search).
            "success_exit_codes": [0, 1],
            "cwd": ".",
        },
    ),
]

