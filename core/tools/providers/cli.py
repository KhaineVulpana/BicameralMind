"""Provider for CLI/subprocess tools."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional

from loguru import logger

from ..models import ToolDefinition, ToolResult
from .base import ToolProviderBase


class CLIToolProvider(ToolProviderBase):
    """Executes CLI commands defined in tool config."""

    async def execute(
        self,
        tool: ToolDefinition,
        params: Dict[str, Any],
        timeout: Optional[float] = None,
    ) -> ToolResult:
        cfg = tool.config or {}
        command = cfg.get("command")
        args = cfg.get("args", [])
        if not command:
            return ToolResult(
                tool_name=tool.name,
                success=False,
                error="Missing command in tool config",
            )

        cmd = [command] if isinstance(command, str) else list(command)
        cmd.extend([self._render_value(a, params) for a in (args or [])])

        stdin_mode = cfg.get("stdin_mode", "none")
        stdin_template = cfg.get("stdin_template")
        env = cfg.get("env") or None
        cwd = cfg.get("cwd") or None
        success_codes = cfg.get("success_exit_codes") or [0]

        input_data = None
        if stdin_mode == "json":
            input_data = json.dumps(params)
        elif stdin_mode == "text":
            if stdin_template:
                input_data = self._render_value(stdin_template, params)
            else:
                input_data = str(params.get("text", ""))

        logger.debug(f"CLI tool: {tool.name} -> {' '.join(cmd)}")

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE if input_data is not None else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=cwd,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input_data.encode("utf-8") if input_data is not None else None),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            return ToolResult(
                tool_name=tool.name,
                success=False,
                error="CLI tool execution timeout",
            )
        except Exception as exc:
            return ToolResult(
                tool_name=tool.name,
                success=False,
                error=str(exc),
            )

        exit_code = proc.returncode if proc else 1
        success = exit_code in success_codes
        output = stdout.decode("utf-8", errors="replace").strip() if stdout else ""
        err_text = stderr.decode("utf-8", errors="replace").strip() if stderr else ""

        return ToolResult(
            tool_name=tool.name,
            success=success,
            output=output,
            error=None if success else (err_text or f"Exit code {exit_code}"),
            metadata={"exit_code": exit_code},
        )

    @staticmethod
    def _render_value(value: Any, params: Dict[str, Any]) -> str:
        if not isinstance(value, str):
            return str(value)
        rendered = value
        for key, val in params.items():
            rendered = rendered.replace(f"{{{key}}}", str(val))
        return rendered
