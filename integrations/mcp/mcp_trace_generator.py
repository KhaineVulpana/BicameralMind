"""MCP Tool Result to ExecutionTrace Conversion"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from core.memory.trace import ExecutionTrace, create_trace
from .tool_executor import ToolExecutionResult, ToolExecutionContext

logger = logging.getLogger(__name__)


def generate_trace_from_tool_result(
    execution_result: ToolExecutionResult
) -> ExecutionTrace:
    """
    Convert tool execution result to ExecutionTrace

    Args:
        execution_result: ToolExecutionResult from tool execution

    Returns:
        ExecutionTrace suitable for learning pipeline
    """
    context = execution_result.context
    tool_result = execution_result.tool_result

    # Build task description
    task = _build_task_description(context)

    # Convert execution steps
    steps = _convert_execution_steps(execution_result.execution_steps)

    # Determine success
    success = tool_result.success

    # Build error message if failed
    error_message = tool_result.error if not success else None

    # Calculate confidence (can be adjusted based on tool result)
    confidence = context.confidence
    if not success:
        # Lower confidence after failure
        confidence = max(0.1, confidence - 0.3)

    # Build tools_called list
    tools_called = [context.tool_name]

    # Create trace
    trace = create_trace(
        task=task,
        hemisphere=context.hemisphere,
        steps=steps,
        bullets_used=context.bullets_used,
        success=success,
        error_message=error_message,
        tools_called=tools_called,
        confidence=confidence,
        metadata={
            "tool_name": context.tool_name,
            "tool_parameters": context.parameters,
            "execution_time": tool_result.execution_time,
            "timestamp": execution_result.timestamp.isoformat(),
            **context.metadata,
        }
    )

    logger.debug(f"Generated trace {trace.trace_id} from tool execution")

    return trace


def _build_task_description(context: ToolExecutionContext) -> str:
    """
    Build human-readable task description

    Args:
        context: Tool execution context

    Returns:
        Task description string
    """
    # Format parameters nicely
    param_str = ", ".join(
        f"{k}={repr(v)}" for k, v in context.parameters.items()
    )

    return f"Execute {context.tool_name}({param_str})"


def _convert_execution_steps(
    steps: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Convert tool execution steps to trace steps format

    Args:
        steps: Raw execution steps from ToolExecutor

    Returns:
        Formatted steps for ExecutionTrace
    """
    converted_steps = []

    for step in steps:
        converted_step = {
            "description": step.get("description", step.get("step", "Unknown step")),
            "success": step.get("success", False),
        }

        # Add error if present
        if "error" in step:
            converted_step["error"] = step["error"]

        # Add execution time if present
        if "execution_time" in step:
            converted_step["execution_time"] = step["execution_time"]

        converted_steps.append(converted_step)

    return converted_steps


def generate_trace_from_tool_call(
    tool_name: str,
    parameters: Dict[str, Any],
    tool_result: Any,
    bullets_used: List[str],
    hemisphere: str = "left",
    confidence: float = 0.5,
    **kwargs
) -> ExecutionTrace:
    """
    Simplified trace generation from raw tool call data

    Args:
        tool_name: Name of tool that was called
        parameters: Parameters passed to tool
        tool_result: Result from tool (success/failure/output)
        bullets_used: List of bullet IDs used for this tool call
        hemisphere: Which hemisphere executed ("left" or "right")
        confidence: Execution confidence (0.0-1.0)
        **kwargs: Additional metadata

    Returns:
        ExecutionTrace
    """
    # Determine success from result
    if isinstance(tool_result, dict):
        success = tool_result.get("success", True)
        error_message = tool_result.get("error")
        output = tool_result.get("output")
    else:
        success = bool(tool_result)
        error_message = None
        output = tool_result

    # Build task description
    param_str = ", ".join(f"{k}={repr(v)}" for k, v in parameters.items())
    task = f"Execute {tool_name}({param_str})"

    # Create simple steps
    steps = [
        {
            "description": f"Call {tool_name}",
            "success": success,
        }
    ]

    if error_message:
        steps[0]["error"] = error_message

    # Create trace
    return create_trace(
        task=task,
        hemisphere=hemisphere,
        steps=steps,
        bullets_used=bullets_used,
        success=success,
        error_message=error_message,
        tools_called=[tool_name],
        confidence=confidence,
        metadata={
            "tool_name": tool_name,
            "tool_parameters": parameters,
            "tool_output": output,
            **kwargs,
        }
    )


class MCPTraceGenerator:
    """
    Stateful trace generator for MCP tool executions

    Maintains history and provides additional utilities for
    trace generation and analysis.
    """

    def __init__(self):
        """Initialize trace generator"""
        self.generated_traces: List[ExecutionTrace] = []

    def generate(self, execution_result: ToolExecutionResult) -> ExecutionTrace:
        """
        Generate trace and store in history

        Args:
            execution_result: Tool execution result

        Returns:
            Generated ExecutionTrace
        """
        trace = generate_trace_from_tool_result(execution_result)
        self.generated_traces.append(trace)

        # Keep only last 100 traces
        if len(self.generated_traces) > 100:
            self.generated_traces = self.generated_traces[-100:]

        return trace

    def get_trace_history(self, limit: int = 10) -> List[ExecutionTrace]:
        """Get recent trace history"""
        return self.generated_traces[-limit:]

    def get_traces_by_tool(self, tool_name: str) -> List[ExecutionTrace]:
        """Get all traces for a specific tool"""
        return [
            trace for trace in self.generated_traces
            if trace.metadata.get("tool_name") == tool_name
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get trace generation statistics"""
        if not self.generated_traces:
            return {
                "total_traces": 0,
                "success_rate": 0.0,
                "tools_used": [],
            }

        total = len(self.generated_traces)
        successful = sum(1 for t in self.generated_traces if t.success)

        # Count tool usage
        tool_counts: Dict[str, int] = {}
        for trace in self.generated_traces:
            tool_name = trace.metadata.get("tool_name")
            if tool_name:
                tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1

        return {
            "total_traces": total,
            "successful_traces": successful,
            "failed_traces": total - successful,
            "success_rate": successful / total if total > 0 else 0.0,
            "tools_used": list(tool_counts.keys()),
            "tool_usage_counts": tool_counts,
        }
