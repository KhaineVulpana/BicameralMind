"""Provider for local Python callables."""

from __future__ import annotations

import asyncio
import importlib
import inspect
from typing import Any, Callable, Dict, Optional

from loguru import logger

from ..models import ToolDefinition, ToolResult
from .base import ToolProviderBase


class LocalToolProvider(ToolProviderBase):
    """Executes Python callables registered by name."""

    def __init__(self) -> None:
        self._callables: Dict[str, Callable[..., Any]] = {}

    def register_callable(self, name: str, func: Callable[..., Any]) -> None:
        self._callables[name] = func

    def _load_entrypoint(self, entrypoint: str) -> Optional[Callable[..., Any]]:
        if not entrypoint or ":" not in entrypoint:
            return None
        module_path, func_name = entrypoint.split(":", 1)
        module = importlib.import_module(module_path)
        return getattr(module, func_name, None)

    async def execute(
        self,
        tool: ToolDefinition,
        params: Dict[str, Any],
        timeout: Optional[float] = None,
    ) -> ToolResult:
        func = self._callables.get(tool.name)
        if not func:
            entrypoint = tool.config.get("entrypoint") if tool.config else None
            func = self._load_entrypoint(entrypoint) if entrypoint else None

        if not func:
            return ToolResult(
                tool_name=tool.name,
                success=False,
                error="Local callable not registered",
            )

        try:
            if inspect.iscoroutinefunction(func):
                if timeout:
                    output = await asyncio.wait_for(func(**params), timeout=timeout)
                else:
                    output = await func(**params)
            else:
                if timeout:
                    output = await asyncio.wait_for(
                        asyncio.to_thread(func, **params),
                        timeout=timeout,
                    )
                else:
                    output = await asyncio.to_thread(func, **params)
        except Exception as exc:
            logger.warning(f"Local tool failed: {tool.name} ({exc})")
            return ToolResult(
                tool_name=tool.name,
                success=False,
                error=str(exc),
            )

        return ToolResult(
            tool_name=tool.name,
            success=True,
            output=output,
        )
