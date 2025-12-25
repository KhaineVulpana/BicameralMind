"""MCP Integration for Bicameral Mind."""
from typing import Any, Dict

from .mcp_client import MCPClient


class MCPIntegration:
    """
    MCP (Model Context Protocol) Integration
    
    Allows bicameral mind to connect to MCP servers for:
    - Tool use
    - External data sources
    - Service integrations
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config.get("mcp", {})
        self.servers = self.config.get("servers", [])
        self.connected = False
        self.client = MCPClient(config)
    
    async def connect(self):
        """Connect to configured MCP servers"""
        await self.client.connect()
        self.connected = self.client.connected
    
    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """Call an MCP tool"""
        return await self.client.call_tool(tool_name=tool_name, parameters=params)
    
    async def disconnect(self):
        """Disconnect from MCP servers"""
        await self.client.disconnect()
        self.connected = False


# Example MCP server configuration for config.yaml:
"""
mcp:
  enabled: true
  servers:
    - name: "filesystem"
      type: "stdio"
      command: "npx"
      args: ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/files"]
    
    - name: "github"
      type: "stdio"  
      command: "npx"
      args: ["-y", "@modelcontextprotocol/server-github"]
      env:
        GITHUB_PERSONAL_ACCESS_TOKEN: "your_token_here"
"""
