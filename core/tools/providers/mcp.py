"""Provider for MCP tools."""

from __future__ import annotations

from typing import Any, Dict, Optional

from loguru import logger

from ..models import ToolDefinition, ToolProvider, ToolResult
from .base import ToolProviderBase


class MCPToolProvider(ToolProviderBase):
    """Executes tools via MCP client."""

    def __init__(self, mcp_client: Any):
        self.mcp_client = mcp_client

    async def execute(
        self,
        tool: ToolDefinition,
        params: Dict[str, Any],
        timeout: Optional[float] = None,
    ) -> ToolResult:
        if tool.provider != ToolProvider.MCP:
            return ToolResult(
                tool_name=tool.name,
                success=False,
                error="Tool provider mismatch",
            )
        if not self.mcp_client:
            return ToolResult(
                tool_name=tool.name,
                success=False,
                error="MCP client not configured",
            )
        try:
            result = await self.mcp_client.call_tool(tool.name, params, timeout=timeout)
        except Exception as exc:
            logger.warning(f"MCP tool failed: {tool.name} ({exc})")
            return ToolResult(
                tool_name=tool.name,
                success=False,
                error=str(exc),
            )
        return ToolResult(
            tool_name=tool.name,
            success=bool(result.success),
            output=result.output,
            error=result.error,
            execution_time=result.execution_time,
            metadata=result.metadata or {},
        )
