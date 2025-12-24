"""MCP Integration Exceptions"""


class MCPError(Exception):
    """Base exception for MCP integration errors"""
    pass


class MCPConnectionError(MCPError):
    """Raised when MCP server connection fails"""
    pass


class MCPToolNotFoundError(MCPError):
    """Raised when requested tool is not available"""
    pass


class MCPToolExecutionError(MCPError):
    """Raised when tool execution fails"""
    pass


class MCPTimeoutError(MCPError):
    """Raised when MCP operation times out"""
    pass


class MCPValidationError(MCPError):
    """Raised when tool parameter validation fails"""
    pass


class MCPLearningError(MCPError):
    """Raised when learning from tool execution fails"""
    pass
