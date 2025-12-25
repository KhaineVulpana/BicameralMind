"""Tool registry with JSON persistence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from loguru import logger

from .models import ToolDefinition, ToolProvider


class ToolRegistry:
    """Registry of available tools with JSON persistence."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = (config or {}).get("tools", {})
        self.registry_path = Path(
            cfg.get("registry_path", "./data/tools/tool_registry.json")
        )
        self.allowed_tools = set(cfg.get("allowed_tools", []))
        self.blocked_tools = set(cfg.get("blocked_tools", []))
        self._tools: Dict[str, ToolDefinition] = {}
        self._loaded = False

    def load(self) -> None:
        """Load registry from disk."""
        if not self.registry_path.exists():
            self._loaded = True
            return
        try:
            data = json.loads(self.registry_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning(f"Failed to read tool registry: {exc}")
            self._loaded = True
            return

        tools = data.get("tools", [])
        self._tools = {}
        for item in tools:
            tool = ToolDefinition.from_dict(item)
            self._tools[tool.name] = tool

        file_allow = data.get("allowed_tools", [])
        file_block = data.get("blocked_tools", [])
        if file_allow:
            self.allowed_tools = set(file_allow)
        if file_block:
            self.blocked_tools = set(file_block)

        self._loaded = True

    def save(self) -> None:
        """Persist registry to disk."""
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "tools": [tool.to_dict() for tool in self._tools.values()],
            "allowed_tools": sorted(self.allowed_tools),
            "blocked_tools": sorted(self.blocked_tools),
        }
        self.registry_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def register(self, tool: ToolDefinition, save: bool = True) -> None:
        """Register or replace a tool definition."""
        self._tools[tool.name] = tool
        if save:
            self.save()

    def register_many(self, tools: Iterable[ToolDefinition], save: bool = True) -> None:
        """Register multiple tool definitions."""
        for tool in tools:
            self._tools[tool.name] = tool
        if save:
            self.save()

    def remove(self, tool_name: str, save: bool = True) -> bool:
        """Remove a tool from the registry."""
        if tool_name not in self._tools:
            return False
        self._tools.pop(tool_name, None)
        if save:
            self.save()
        return True

    def set_enabled(self, tool_name: str, enabled: bool, save: bool = True) -> bool:
        """Enable/disable a tool."""
        tool = self._tools.get(tool_name)
        if not tool:
            return False
        tool.enabled = bool(enabled)
        if save:
            self.save()
        return True

    def list_tools(self, enabled_only: bool = True) -> List[ToolDefinition]:
        """List tools in the registry."""
        tools = list(self._tools.values())
        if enabled_only:
            tools = [t for t in tools if t.enabled]
        return tools

    def get_tool(self, tool_name: str, allow_disabled: bool = False) -> Optional[ToolDefinition]:
        """Fetch a tool by name."""
        tool = self._tools.get(tool_name)
        if not tool:
            return None
        if not allow_disabled and not tool.enabled:
            return None
        if not self._is_allowed(tool.name):
            return None
        return tool

    def _is_allowed(self, tool_name: str) -> bool:
        if tool_name in self.blocked_tools:
            return False
        if not self.allowed_tools:
            return True
        return tool_name in self.allowed_tools

    def list_by_provider(self, provider: ToolProvider) -> List[ToolDefinition]:
        """List tools for a provider."""
        return [t for t in self._tools.values() if t.provider == provider]

    def is_loaded(self) -> bool:
        return self._loaded
