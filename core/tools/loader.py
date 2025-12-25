"""Tool registry bootstrap and discovery."""

from __future__ import annotations

import importlib
import pkgutil
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from .models import ToolDefinition, ToolProvider
from .registry import ToolRegistry
from .index import ToolIndex
from .executor import ToolExecutor
from .providers import CLIToolProvider, HTTPToolProvider, LocalToolProvider, MCPToolProvider


def discover_builtin_tools(
    local_provider: LocalToolProvider,
) -> List[ToolDefinition]:
    """Discover tools from core.tools.builtin modules."""
    tools: List[ToolDefinition] = []
    package = "core.tools.builtin"
    module = importlib.import_module(package)

    for info in pkgutil.iter_modules(module.__path__, module.__name__ + "."):
        mod = importlib.import_module(info.name)
        mod_tools = getattr(mod, "TOOL_DEFINITIONS", [])
        for tool in mod_tools:
            if isinstance(tool, ToolDefinition):
                tools.append(tool)
            elif isinstance(tool, dict):
                tools.append(ToolDefinition.from_dict(tool))

        callables = getattr(mod, "TOOL_CALLABLES", {})
        for name, func in (callables or {}).items():
            local_provider.register_callable(name, func)

    return tools


def initialize_tools(
    config: Dict[str, Any],
    mcp_client: Optional[Any] = None,
) -> Tuple[ToolRegistry, ToolExecutor, Optional[ToolIndex]]:
    """Initialize tool registry, providers, and executor."""
    registry = ToolRegistry(config)
    registry.load()

    tools_cfg = (config or {}).get("tools", {})
    auto_discover = bool(tools_cfg.get("auto_discover", True))
    auto_index = bool(tools_cfg.get("auto_index", True))

    local_provider = LocalToolProvider()
    cli_provider = CLIToolProvider()
    http_provider = HTTPToolProvider()
    mcp_provider = MCPToolProvider(mcp_client) if mcp_client else None

    if auto_discover:
        builtin_tools = discover_builtin_tools(local_provider)
        if builtin_tools:
            registry.register_many(builtin_tools, save=False)
            registry.save()
            logger.info(f"Registered {len(builtin_tools)} built-in tools")

    tool_index = None
    if auto_index:
        try:
            tool_index = ToolIndex(config)
            tool_index.index_tools(registry.list_tools(enabled_only=False))
        except Exception as exc:
            logger.warning(f"Tool index unavailable: {exc}")

    executor = ToolExecutor(
        registry=registry,
        local_provider=local_provider,
        cli_provider=cli_provider,
        http_provider=http_provider,
        mcp_provider=mcp_provider,
        default_timeout=float(tools_cfg.get("default_timeout", 60)),
    )

    return registry, executor, tool_index


async def register_mcp_tools(
    registry: ToolRegistry,
    tool_index: Optional[ToolIndex],
    mcp_client: Any,
) -> int:
    """Register MCP tools into the registry and index."""
    if not mcp_client:
        return 0
    try:
        tools = await mcp_client.list_tools()
    except Exception as exc:
        logger.warning(f"Failed to list MCP tools: {exc}")
        return 0

    definitions: List[ToolDefinition] = []
    for tool in tools:
        tags = ["mcp"]
        server_name = getattr(tool, "server_name", "")
        if server_name:
            tags.append(server_name)
        definitions.append(
            ToolDefinition(
                name=tool.name,
                description=tool.description or "",
                provider=ToolProvider.MCP,
                input_schema=tool.parameters or {},
                output_schema=tool.schema or {},
                tags=tags,
                config={"server": server_name},
            )
        )

    if not definitions:
        return 0

    registry.register_many(definitions, save=True)
    if tool_index:
        tool_index.index_tools(definitions)
    return len(definitions)
