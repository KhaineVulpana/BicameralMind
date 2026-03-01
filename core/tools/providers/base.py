"""Base provider interface."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..models import ToolDefinition, ToolResult


class ToolProviderBase:
    """Base class for tool providers."""

    async def execute(
        self,
        tool: ToolDefinition,
        params: Dict[str, Any],
        timeout: Optional[float] = None,
    ) -> ToolResult:
        raise NotImplementedError
