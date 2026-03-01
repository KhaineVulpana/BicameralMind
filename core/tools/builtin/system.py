"""System-oriented built-in tools."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from ..models import ToolDefinition, ToolProvider


def open_path(path: str, allow_outside_repo: bool = False) -> str:
    """Open a file/folder using the OS default handler.

    On Windows this uses os.startfile(). For safety, paths are restricted to the
    current working directory tree unless allow_outside_repo is True.
    """
    if not path or not str(path).strip():
        raise ValueError("path is required")

    raw = str(path).strip().strip('"')
    resolved = Path(raw).expanduser()
    if not resolved.is_absolute():
        resolved = (Path.cwd() / resolved)
    resolved = resolved.resolve()

    if not allow_outside_repo:
        root = Path.cwd().resolve()
        if not resolved.is_relative_to(root):
            raise PermissionError(
                f"Refusing to open path outside repo root: {resolved} (set allow_outside_repo=true to override)"
            )

    if not resolved.exists():
        raise FileNotFoundError(str(resolved))

    os.startfile(str(resolved))  # type: ignore[attr-defined]
    return f"Opened: {resolved}"


TOOL_DEFINITIONS = [
    ToolDefinition(
        name="local.open_path",
        description="Open a file or folder in the OS (Explorer/Finder).",
        provider=ToolProvider.LOCAL,
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "allow_outside_repo": {"type": "boolean"},
            },
            "required": ["path"],
        },
        output_schema={"type": "string"},
        tags=["local", "system", "ui"],
        risk="medium",
        config={"entrypoint": "core.tools.builtin.system:open_path"},
    ),
]


TOOL_CALLABLES = {
    "local.open_path": open_path,
}

