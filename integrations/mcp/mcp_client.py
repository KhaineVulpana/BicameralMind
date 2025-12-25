"""MCP Client Implementation"""
import asyncio
import logging
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .exceptions import (
    MCPConnectionError,
    MCPToolNotFoundError,
    MCPTimeoutError,
)

logger = logging.getLogger(__name__)


@dataclass
class MCPTool:
    """Represents an MCP tool with metadata"""
    name: str
    description: str
    parameters: Dict[str, Any]
    server_name: str
    schema: Optional[Dict[str, Any]] = None

    def validate_parameters(self, params: Dict[str, Any]) -> bool:
        """Validate parameters against tool schema"""
        if not self.parameters:
            return True

        # Basic validation - check required parameters exist
        required = self.parameters.get("required", [])
        for req in required:
            if req not in params:
                return False

        return True


@dataclass
class MCPServer:
    """Represents an MCP server connection"""
    name: str
    type: str  # stdio, http, etc.
    command: Optional[str] = None
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    endpoint: Optional[str] = None
    cwd: Optional[str] = None
    enabled: bool = True
    connected: bool = False
    mock: bool = False
    tools: List[MCPTool] = field(default_factory=list)
    last_connected: Optional[datetime] = None
    connection_attempts: int = 0
    session: Optional[Any] = None


@dataclass
class MCPToolResult:
    """Result from tool execution"""
    tool_name: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class MCPClient:
    """
    MCP (Model Context Protocol) Client

    Manages connections to MCP servers and tool execution.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize MCP client

        Args:
            config: Configuration dict with MCP settings
        """
        self.config = config.get("mcp", {})
        self.enabled = self.config.get("enabled", False)
        self.connection_timeout = self.config.get("connection_timeout", 30)
        self.tool_timeout = self.config.get("tool_timeout", 60)
        self.max_retries = self.config.get("max_retries", 3)
        self.mock_on_failure = self.config.get("mock_on_failure", True)

        self.servers: Dict[str, MCPServer] = {}
        self.tools: Dict[str, MCPTool] = {}  # tool_name -> MCPTool
        self.connected = False
        self._connection_stacks: Dict[str, AsyncExitStack] = {}

        # Tool filtering
        self.allowed_tools = set(self.config.get("allowed_tools", []))
        self.blocked_tools = set(self.config.get("blocked_tools", []))

        # Statistics
        self.stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_execution_time": 0.0,
        }

        # Initialize servers from config
        self._init_servers()

    def _init_servers(self):
        """Initialize server configurations"""
        server_configs = self.config.get("servers", [])

        for server_config in server_configs:
            if not server_config.get("enabled", True):
                continue

            server = MCPServer(
                name=server_config["name"],
                type=server_config.get("type", "stdio"),
                command=server_config.get("command"),
                args=server_config.get("args", []),
                env={k: str(v) for k, v in (server_config.get("env") or {}).items()},
                endpoint=server_config.get("endpoint") or server_config.get("url"),
                cwd=server_config.get("cwd"),
                enabled=server_config.get("enabled", True),
            )

            self.servers[server.name] = server
            logger.info(f"Initialized MCP server config: {server.name}")

    async def connect(self):
        """Connect to all configured MCP servers"""
        if not self.enabled:
            logger.info("MCP is disabled in configuration")
            return

        if not self.servers:
            logger.warning("No MCP servers configured")
            return

        self.tools.clear()

        logger.info(f"Connecting to {len(self.servers)} MCP servers...")

        # Connect to each server
        for server_name, server in self.servers.items():
            if not server.enabled:
                continue
            server.mock = False
            server.session = None

            try:
                await self._connect_server(server)
            except Exception as e:
                logger.error(f"Failed to connect to {server_name}: {e}")
                server.connected = False

        # Check if any servers connected
        connected_count = sum(1 for s in self.servers.values() if s.connected)
        if connected_count > 0:
            self.connected = True
            logger.info(f"Connected to {connected_count}/{len(self.servers)} MCP servers")
        else:
            logger.warning("No MCP servers connected")

    async def _connect_server(self, server: MCPServer):
        """
        Connect to a single MCP server

        Args:
            server: MCPServer to connect to
        """
        logger.info(f"Connecting to MCP server: {server.name} (type: {server.type})")

        try:
            if server.type == "stdio":
                await self._connect_stdio_server(server)
            elif server.type == "http" or server.type == "api":
                await self._connect_http_server(server)
            else:
                raise MCPConnectionError(f"Unsupported server type: {server.type}")

            server.connected = True
            server.last_connected = datetime.now()
            server.connection_attempts += 1

            # Discover tools
            await self._discover_tools(server)

            logger.info(f"Connected to {server.name}, discovered {len(server.tools)} tools")

        except Exception as e:
            server.connection_attempts += 1
            server.connected = False
            server.session = None
            if self.mock_on_failure:
                logger.warning(f"Falling back to mock tools for {server.name}: {e}")
                server.mock = True
                await self._discover_tools(server)
                return
            raise MCPConnectionError(f"Failed to connect to {server.name}: {e}")

    async def _connect_stdio_server(self, server: MCPServer):
        """
        Connect to a stdio-based MCP server

        Args:
            server: MCPServer with stdio configuration
        """
        if not server.command:
            raise MCPConnectionError("Missing command for stdio server")

        from mcp.client.session import ClientSession
        from mcp.client.stdio import StdioServerParameters, stdio_client

        logger.debug(f"STDIO server {server.name}: {server.command} {' '.join(server.args)}")

        params = StdioServerParameters(
            command=server.command,
            args=server.args or [],
            env=server.env or None,
            cwd=server.cwd,
        )

        stack = AsyncExitStack()
        read_stream, write_stream = await stack.enter_async_context(stdio_client(params))
        session = ClientSession(
            read_stream,
            write_stream,
            read_timeout_seconds=timedelta(seconds=self.connection_timeout),
        )
        await stack.enter_async_context(session)
        await session.initialize()

        self._connection_stacks[server.name] = stack
        server.session = session

    async def _connect_http_server(self, server: MCPServer):
        """
        Connect to an HTTP/API-based MCP server

        Args:
            server: MCPServer with HTTP configuration
        """
        if not server.endpoint:
            raise MCPConnectionError("Missing endpoint for HTTP server")

        from mcp.client.session import ClientSession
        from mcp.client.streamable_http import streamable_http_client

        logger.debug(f"HTTP server {server.name}: {server.endpoint}")

        stack = AsyncExitStack()
        read_stream, write_stream, _ = await stack.enter_async_context(
            streamable_http_client(server.endpoint)
        )
        session = ClientSession(
            read_stream,
            write_stream,
            read_timeout_seconds=timedelta(seconds=self.connection_timeout),
        )
        await stack.enter_async_context(session)
        await session.initialize()

        self._connection_stacks[server.name] = stack
        server.session = session

    async def _discover_tools(self, server: MCPServer):
        """
        Discover available tools from a server

        Args:
            server: Connected MCPServer
        """
        server.tools = []

        tools_payload: List[Dict[str, Any]] = []
        if server.session:
            cursor = None
            while True:
                result = await server.session.list_tools(cursor=cursor)
                for tool in result.tools or []:
                    tools_payload.append(
                        {
                            "name": tool.name,
                            "description": tool.description or "",
                            "parameters": tool.inputSchema or {},
                            "schema": tool.outputSchema,
                        }
                    )
                cursor = result.nextCursor
                if not cursor:
                    break
        else:
            tools_payload = self._get_mock_tools(server.name)

        for tool_data in tools_payload:
            tool = MCPTool(
                name=tool_data["name"],
                description=tool_data.get("description", ""),
                parameters=tool_data.get("parameters", {}),
                server_name=server.name,
                schema=tool_data.get("schema"),
            )

            if self._is_tool_allowed(tool.name):
                server.tools.append(tool)
                self.tools[tool.name] = tool
                logger.debug(f"Discovered tool: {tool.name}")

    def _get_mock_tools(self, server_name: str) -> List[Dict[str, Any]]:
        """Get mock tools for testing (will be replaced with real discovery)"""
        if server_name == "filesystem":
            return [
                {
                    "name": "read_file",
                    "description": "Read contents of a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "File path"},
                        },
                        "required": ["path"],
                    },
                },
                {
                    "name": "write_file",
                    "description": "Write contents to a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "File path"},
                            "content": {"type": "string", "description": "File content"},
                        },
                        "required": ["path", "content"],
                    },
                },
                {
                    "name": "list_directory",
                    "description": "List files in a directory",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Directory path"},
                        },
                        "required": ["path"],
                    },
                },
            ]
        elif server_name == "github":
            return [
                {
                    "name": "search_repos",
                    "description": "Search GitHub repositories",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "limit": {"type": "integer", "description": "Max results"},
                        },
                        "required": ["query"],
                    },
                },
            ]
        return []

    def _is_tool_allowed(self, tool_name: str) -> bool:
        """Check if tool is allowed to be used"""
        # If in blocklist, reject
        if tool_name in self.blocked_tools:
            return False

        # If allowlist is empty, allow all (except blocked)
        if not self.allowed_tools:
            return True

        # If allowlist exists, only allow tools in it
        return tool_name in self.allowed_tools

    async def call_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        timeout: Optional[float] = None
    ) -> MCPToolResult:
        """
        Execute an MCP tool

        Args:
            tool_name: Name of tool to execute
            parameters: Tool parameters
            timeout: Optional timeout override

        Returns:
            MCPToolResult with execution results
        """
        start_time = asyncio.get_event_loop().time()

        # Check if tool exists
        if tool_name not in self.tools:
            self.stats["failed_calls"] += 1
            return MCPToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Tool not found: {tool_name}",
            )

        tool = self.tools[tool_name]

        # Validate parameters
        if not tool.validate_parameters(parameters):
            self.stats["failed_calls"] += 1
            return MCPToolResult(
                tool_name=tool_name,
                success=False,
                error="Invalid parameters",
            )

        # Execute tool
        timeout = timeout or self.tool_timeout

        try:
            result = await asyncio.wait_for(
                self._execute_tool(tool, parameters),
                timeout=timeout
            )

            execution_time = asyncio.get_event_loop().time() - start_time

            # Update stats
            self.stats["total_calls"] += 1
            self.stats["total_execution_time"] += execution_time

            if result.success:
                self.stats["successful_calls"] += 1
            else:
                self.stats["failed_calls"] += 1

            result.execution_time = execution_time
            return result

        except asyncio.TimeoutError:
            execution_time = asyncio.get_event_loop().time() - start_time
            self.stats["failed_calls"] += 1
            self.stats["total_calls"] += 1

            return MCPToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Tool execution timeout after {timeout}s",
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            self.stats["failed_calls"] += 1
            self.stats["total_calls"] += 1

            return MCPToolResult(
                tool_name=tool_name,
                success=False,
                error=str(e),
                execution_time=execution_time,
            )

    async def _execute_tool(
        self,
        tool: MCPTool,
        parameters: Dict[str, Any]
    ) -> MCPToolResult:
        """
        Execute tool on MCP server

        Args:
            tool: MCPTool to execute
            parameters: Tool parameters

        Returns:
            MCPToolResult
        """
        logger.debug(f"Executing tool: {tool.name} with params: {parameters}")

        server = self.servers.get(tool.server_name)
        if not server or not server.session:
            if self.mock_on_failure:
                return MCPToolResult(
                    tool_name=tool.name,
                    success=True,
                    output=f"Mock result from {tool.name}",
                    metadata={"server": tool.server_name, "mock": True},
                )
            return MCPToolResult(
                tool_name=tool.name,
                success=False,
                error="Server not connected",
            )

        try:
            result = await server.session.call_tool(
                tool.name,
                arguments=parameters,
                read_timeout_seconds=timedelta(seconds=self.tool_timeout),
            )
        except Exception as e:
            return MCPToolResult(
                tool_name=tool.name,
                success=False,
                error=str(e),
                metadata={"server": tool.server_name},
            )

        output = None
        if result.structuredContent is not None:
            output = result.structuredContent
        elif result.content:
            blocks = []
            for block in result.content:
                if hasattr(block, "text"):
                    blocks.append(block.text)
                elif hasattr(block, "data"):
                    blocks.append(block.data)
                elif hasattr(block, "model_dump"):
                    blocks.append(block.model_dump())
                else:
                    blocks.append(str(block))
            output = blocks[0] if len(blocks) == 1 else blocks

        return MCPToolResult(
            tool_name=tool.name,
            success=not result.isError,
            output=output,
            error="Tool returned error" if result.isError else None,
            metadata={"server": tool.server_name},
        )

    async def list_tools(self) -> List[MCPTool]:
        """Get list of all available tools"""
        return list(self.tools.values())

    def get_tool(self, tool_name: str) -> Optional[MCPTool]:
        """Get tool by name"""
        return self.tools.get(tool_name)

    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics"""
        stats = dict(self.stats)

        if stats["total_calls"] > 0:
            stats["success_rate"] = stats["successful_calls"] / stats["total_calls"]
            stats["avg_execution_time"] = stats["total_execution_time"] / stats["total_calls"]
        else:
            stats["success_rate"] = 0.0
            stats["avg_execution_time"] = 0.0

        stats["connected_servers"] = sum(1 for s in self.servers.values() if s.connected)
        stats["total_servers"] = len(self.servers)
        stats["available_tools"] = len(self.tools)

        return stats

    async def disconnect(self):
        """Disconnect from all MCP servers"""
        logger.info("Disconnecting from MCP servers...")

        for server in self.servers.values():
            if server.connected:
                try:
                    await self._disconnect_server(server)
                except Exception as e:
                    logger.error(f"Error disconnecting from {server.name}: {e}")

        self.connected = False
        self.tools.clear()

        logger.info("Disconnected from all MCP servers")

    async def _disconnect_server(self, server: MCPServer):
        """Disconnect from a single server"""
        stack = self._connection_stacks.pop(server.name, None)
        if stack:
            await stack.aclose()
        server.connected = False
        server.session = None
        server.tools.clear()
