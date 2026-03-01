"""MCP Integration for Bicameral Mind"""

# Core components
from .mcp_client import MCPClient, MCPServer, MCPTool, MCPToolResult
from .tool_executor import ToolExecutor, ToolExecutionContext, ToolExecutionResult
from .mcp_trace_generator import (
    MCPTraceGenerator,
    generate_trace_from_tool_result,
    generate_trace_from_tool_call,
)
from .mcp_learning_integration import MCPLearningIntegration, MCPLearningResult

# Exceptions
from .exceptions import (
    MCPError,
    MCPConnectionError,
    MCPToolNotFoundError,
    MCPToolExecutionError,
    MCPTimeoutError,
    MCPValidationError,
    MCPLearningError,
)

__all__ = [
    # Core
    "MCPClient",
    "MCPServer",
    "MCPTool",
    "MCPToolResult",
    "ToolExecutor",
    "ToolExecutionContext",
    "ToolExecutionResult",
    "MCPTraceGenerator",
    "generate_trace_from_tool_result",
    "generate_trace_from_tool_call",
    "MCPLearningIntegration",
    "MCPLearningResult",
    # Exceptions
    "MCPError",
    "MCPConnectionError",
    "MCPToolNotFoundError",
    "MCPToolExecutionError",
    "MCPTimeoutError",
    "MCPValidationError",
    "MCPLearningError",
]
