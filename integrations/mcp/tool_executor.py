"""Tool Executor with comprehensive logging and error handling"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

from .mcp_client import MCPClient, MCPToolResult
from .exceptions import MCPToolExecutionError

logger = logging.getLogger(__name__)


@dataclass
class ToolExecutionContext:
    """Context for tool execution"""
    tool_name: str
    parameters: Dict[str, Any]
    hemisphere: str  # "left" or "right"
    confidence: float = 0.5
    expected_success: bool = True
    bullets_used: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolExecutionResult:
    """Extended result with execution context"""
    tool_result: MCPToolResult
    context: ToolExecutionContext
    timestamp: datetime
    execution_steps: List[Dict[str, Any]] = field(default_factory=list)


class ToolExecutor:
    """
    Safe tool execution with comprehensive logging

    Wraps MCP client and adds:
    - Parameter validation
    - Error recovery
    - Detailed logging
    - Execution context tracking
    """

    def __init__(self, mcp_client: MCPClient):
        """
        Initialize tool executor

        Args:
            mcp_client: Connected MCP client
        """
        self.mcp_client = mcp_client
        self.execution_history: List[ToolExecutionResult] = []

    async def execute(
        self,
        context: ToolExecutionContext,
        timeout: Optional[float] = None
    ) -> ToolExecutionResult:
        """
        Execute tool with full context tracking

        Args:
            context: Tool execution context
            timeout: Optional timeout override

        Returns:
            ToolExecutionResult with execution details
        """
        logger.info(
            f"Executing tool: {context.tool_name} "
            f"(hemisphere: {context.hemisphere}, "
            f"confidence: {context.confidence:.2f})"
        )

        execution_steps = []
        timestamp = datetime.now()

        # Step 1: Validate tool exists
        execution_steps.append({
            "step": "validate_tool",
            "description": f"Checking if tool '{context.tool_name}' exists",
            "success": True,
            "timestamp": datetime.now().isoformat(),
        })

        tool = self.mcp_client.get_tool(context.tool_name)
        if not tool:
            execution_steps[-1]["success"] = False
            execution_steps[-1]["error"] = f"Tool '{context.tool_name}' not found"

            result = ToolExecutionResult(
                tool_result=MCPToolResult(
                    tool_name=context.tool_name,
                    success=False,
                    error=f"Tool not found: {context.tool_name}",
                ),
                context=context,
                timestamp=timestamp,
                execution_steps=execution_steps,
            )

            self._log_execution(result)
            return result

        # Step 2: Validate parameters
        execution_steps.append({
            "step": "validate_parameters",
            "description": "Validating tool parameters against schema",
            "success": True,
            "timestamp": datetime.now().isoformat(),
        })

        if not tool.validate_parameters(context.parameters):
            execution_steps[-1]["success"] = False
            execution_steps[-1]["error"] = "Parameter validation failed"

            logger.warning(
                f"Invalid parameters for {context.tool_name}: {context.parameters}"
            )

            result = ToolExecutionResult(
                tool_result=MCPToolResult(
                    tool_name=context.tool_name,
                    success=False,
                    error="Invalid parameters",
                ),
                context=context,
                timestamp=timestamp,
                execution_steps=execution_steps,
            )

            self._log_execution(result)
            return result

        # Step 3: Execute tool
        execution_steps.append({
            "step": "execute_tool",
            "description": f"Executing {context.tool_name}",
            "timestamp": datetime.now().isoformat(),
        })

        try:
            tool_result = await self.mcp_client.call_tool(
                tool_name=context.tool_name,
                parameters=context.parameters,
                timeout=timeout,
            )

            execution_steps[-1]["success"] = tool_result.success
            execution_steps[-1]["execution_time"] = tool_result.execution_time

            if not tool_result.success:
                execution_steps[-1]["error"] = tool_result.error
                logger.warning(f"Tool execution failed: {tool_result.error}")
            else:
                logger.info(
                    f"Tool executed successfully in {tool_result.execution_time:.2f}s"
                )

            result = ToolExecutionResult(
                tool_result=tool_result,
                context=context,
                timestamp=timestamp,
                execution_steps=execution_steps,
            )

            self._log_execution(result)
            return result

        except Exception as e:
            execution_steps[-1]["success"] = False
            execution_steps[-1]["error"] = str(e)

            logger.error(f"Tool execution exception: {e}")

            result = ToolExecutionResult(
                tool_result=MCPToolResult(
                    tool_name=context.tool_name,
                    success=False,
                    error=str(e),
                ),
                context=context,
                timestamp=timestamp,
                execution_steps=execution_steps,
            )

            self._log_execution(result)
            return result

    def _log_execution(self, result: ToolExecutionResult):
        """Log execution to history"""
        self.execution_history.append(result)

        # Keep only last 100 executions
        if len(self.execution_history) > 100:
            self.execution_history = self.execution_history[-100:]

    def get_execution_history(self, limit: int = 10) -> List[ToolExecutionResult]:
        """Get recent execution history"""
        return self.execution_history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get executor statistics"""
        if not self.execution_history:
            return {
                "total_executions": 0,
                "success_rate": 0.0,
                "avg_execution_time": 0.0,
            }

        total = len(self.execution_history)
        successful = sum(1 for r in self.execution_history if r.tool_result.success)
        total_time = sum(
            r.tool_result.execution_time
            for r in self.execution_history
            if r.tool_result.execution_time
        )

        return {
            "total_executions": total,
            "successful_executions": successful,
            "failed_executions": total - successful,
            "success_rate": successful / total if total > 0 else 0.0,
            "avg_execution_time": total_time / total if total > 0 else 0.0,
        }
