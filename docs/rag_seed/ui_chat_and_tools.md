# Chat and tool usage

Chat basics:
- Send a message in the Chat tab to get the final response.
- "View agent responses" expands to show left/right outputs.
- Use chat mode to force left, right, or auto.

Slash commands:
- /help
- /open <path>
- /tool <tool_name> <json_params?>

Example:
- /tool cli.rg {"args":["-n","AgenticRAG","integrations/rag/agentic_rag.py"]}

High-risk tool access:
- High-risk tools are blocked by default in chat.
- Enable in the Tools tab under "Chat Tool Access".
- High-risk tools include shell or write operations.

MCP servers:
- MCP tools appear when mcp.enabled is true and servers are enabled.
- Use the Tools tab to enable or disable MCP servers.
- MCP tools are auto-registered into the tool registry.
