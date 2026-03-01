# Tool creation playbook

Goal: add tools that are safe, testable, and discoverable.

Tool types:
- local: Python callable registered in the process.
- cli: shell command wrappers with args and working dir.
- http: REST calls with a schema.
- mcp: tools provided by an MCP server.

Register a tool definition:
- POST /api/tools/register with a ToolDefinition payload.
- The tool registry persists in tools.registry_path.

Example JSON:
```json
{
  "definition": {
    "name": "local.example_tool",
    "description": "Short, precise description of the tool",
    "provider": "local",
    "input_schema": {
      "type": "object",
      "properties": {
        "message": { "type": "string" }
      },
      "required": ["message"]
    },
    "output_schema": { "type": "object" },
    "tags": ["example"],
    "risk": "low",
    "timeout": 30,
    "enabled": true,
    "config": {},
    "metadata": {}
  }
}
```

Safety guidance:
- Prefer low-risk tools and explicit schemas.
- For high-risk tools, require human confirmation or restrict to admins.
- Log tool usage and review failures.

Design tips:
- Make tool outputs deterministic and structured when possible.
- Keep tool names stable to avoid breaking references.
- Document parameters with clear units and constraints.
