"""Tool executor with validation and logging."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional

from loguru import logger

from .models import ToolExecutionContext, ToolExecutionRecord, ToolResult, ToolProvider
from .registry import ToolRegistry
from .validation import validate_parameters
from .providers import CLIToolProvider, HTTPToolProvider, LocalToolProvider, MCPToolProvider


class ToolExecutor:
    """Executes tools using provider implementations."""

    def __init__(
        self,
        registry: ToolRegistry,
        local_provider: Optional[LocalToolProvider] = None,
        cli_provider: Optional[CLIToolProvider] = None,
        http_provider: Optional[HTTPToolProvider] = None,
        mcp_provider: Optional[MCPToolProvider] = None,
        default_timeout: float = 60.0,
    ):
        self.registry = registry
        self.default_timeout = default_timeout
        self.providers = {
            ToolProvider.LOCAL.value: local_provider or LocalToolProvider(),
            ToolProvider.CLI.value: cli_provider or CLIToolProvider(),
            ToolProvider.HTTP.value: http_provider or HTTPToolProvider(),
            ToolProvider.MCP.value: mcp_provider,
        }
        self.execution_history: list[ToolExecutionRecord] = []

    async def execute(
        self,
        context: ToolExecutionContext,
        timeout: Optional[float] = None,
    ) -> ToolExecutionRecord:
        start = time.perf_counter()
        steps = []

        tool = self.registry.get_tool(context.tool_name)
        if not tool:
            result = ToolResult(
                tool_name=context.tool_name,
                success=False,
                error="Tool not found or blocked",
            )
            record = ToolExecutionRecord(context=context, result=result, execution_steps=steps)
            self._log_execution(record)
            return record

        steps.append({
            "step": "validate_parameters",
            "success": True,
        })
        ok, errors = validate_parameters(tool.input_schema, context.parameters)
        if not ok:
            steps[-1]["success"] = False
            steps[-1]["error"] = "; ".join(errors)
            result = ToolResult(
                tool_name=tool.name,
                success=False,
                error="Invalid parameters",
                metadata={"errors": errors},
            )
            record = ToolExecutionRecord(context=context, result=result, execution_steps=steps)
            self._log_execution(record)
            return record

        steps.append({
            "step": "execute_tool",
        })
        provider_key = tool.provider.value if isinstance(tool.provider, ToolProvider) else str(tool.provider)
        provider = self._get_provider(provider_key)
        if not provider:
            steps[-1]["success"] = False
            steps[-1]["error"] = "Provider not configured"
            result = ToolResult(
                tool_name=tool.name,
                success=False,
                error="Provider not configured",
            )
            record = ToolExecutionRecord(context=context, result=result, execution_steps=steps)
            self._log_execution(record)
            return record

        final_timeout = timeout or tool.timeout or self.default_timeout
        try:
            result = await provider.execute(
                tool,
                context.parameters,
                timeout=final_timeout,
            )
            steps[-1]["success"] = result.success
            steps[-1]["duration_ms"] = int((time.perf_counter() - start) * 1000)
        except asyncio.TimeoutError:
            result = ToolResult(
                tool_name=tool.name,
                success=False,
                error="Tool execution timeout",
            )
            steps[-1]["success"] = False
            steps[-1]["error"] = "Tool execution timeout"

        result.execution_time = time.perf_counter() - start
        record = ToolExecutionRecord(context=context, result=result, execution_steps=steps)
        self._log_execution(record)
        return record

    def _get_provider(self, provider_key: str):
        return self.providers.get(provider_key)

    def _log_execution(self, record: ToolExecutionRecord) -> None:
        self.execution_history.append(record)
        if len(self.execution_history) > 1000:
            self.execution_history = self.execution_history[-1000:]

        if record.result.success:
            logger.info(f"Tool OK: {record.context.tool_name}")
        else:
            logger.warning(
                f"Tool FAIL: {record.context.tool_name} -> {record.result.error}"
            )

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.execution_history)
        if total == 0:
            return {"total_executions": 0, "success_rate": 0.0}
        success = sum(1 for r in self.execution_history if r.result.success)
        return {
            "total_executions": total,
            "successful_executions": success,
            "failed_executions": total - success,
            "success_rate": success / total if total else 0.0,
        }
