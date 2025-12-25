# Tool Registry (Framework-Agnostic)

This project now supports a framework-agnostic tool registry. Tools can be:

- local Python callables
- CLI/subprocess tools
- HTTP tools
- MCP tools (optional adapter)

## Registry File

Default path: `./data/tools/tool_registry.json`

Minimal JSON structure:

```json
{
  "version": 1,
  "tools": [
    {
      "name": "local.echo",
      "description": "Echo back the provided text.",
      "provider": "local",
      "input_schema": {
        "type": "object",
        "properties": { "text": { "type": "string" } },
        "required": ["text"]
      },
      "output_schema": { "type": "string" },
      "tags": ["local", "utility"],
      "version": "0.1.0",
      "enabled": true,
      "risk": "low",
      "config": {
        "entrypoint": "core.tools.builtin.basic:echo"
      }
    },
    {
      "name": "cli.list_dir",
      "description": "List a directory using the OS shell.",
      "provider": "cli",
      "input_schema": {
        "type": "object",
        "properties": { "path": { "type": "string" } },
        "required": ["path"]
      },
      "output_schema": { "type": "string" },
      "tags": ["cli", "filesystem"],
      "enabled": false,
      "config": {
        "command": "python",
        "args": ["-c", "import os,sys;print('\\n'.join(os.listdir(sys.argv[1])))", "{path}"]
      }
    },
    {
      "name": "http.get_json",
      "description": "HTTP GET request returning JSON.",
      "provider": "http",
      "input_schema": {
        "type": "object",
        "properties": { "url": { "type": "string" } },
        "required": ["url"]
      },
      "output_schema": { "type": "object" },
      "tags": ["http", "network"],
      "enabled": false,
      "config": {
        "method": "GET",
        "url": "{url}",
        "headers": { "Accept": "application/json" }
      }
    }
  ],
  "allowed_tools": [],
  "blocked_tools": []
}
```

## Indexing

Tool metadata is indexed in Chroma for semantic discovery.
Default index path: `./data/vector_store/tools` (collection `tool_registry`).

## Bootstrapping

Use `core.tools.initialize_tools(config, mcp_client=None)` to:

- load the registry
- auto-register built-in tools (optional)
- build/update the vector index
- get a `ToolExecutor` instance

## MCP Adapter

MCP tools are still supported via the adapter provider. They can be registered
into the same registry, but are optional.
