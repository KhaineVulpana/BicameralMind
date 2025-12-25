"""Tool models for the framework-agnostic tool registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ToolProvider(str, Enum):
    """Tool provider types."""

    LOCAL = "local"
    CLI = "cli"
    HTTP = "http"
    MCP = "mcp"


@dataclass
class ToolDefinition:
    """Definition of a tool in the registry."""

    name: str
    description: str
    provider: ToolProvider
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    version: str = "0.1.0"
    enabled: bool = True
    risk: str = "low"
    timeout: Optional[float] = None
    config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize tool definition."""
        return {
            "name": self.name,
            "description": self.description,
            "provider": self.provider.value if isinstance(self.provider, ToolProvider) else self.provider,
            "input_schema": self.input_schema or {},
            "output_schema": self.output_schema or {},
            "tags": self.tags or [],
            "version": self.version,
            "enabled": bool(self.enabled),
            "risk": self.risk,
            "timeout": self.timeout,
            "config": self.config or {},
            "metadata": self.metadata or {},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolDefinition":
        """Deserialize tool definition."""
        provider = data.get("provider", ToolProvider.LOCAL.value)
        if not isinstance(provider, ToolProvider):
            try:
                provider = ToolProvider(provider)
            except ValueError:
                provider = ToolProvider.LOCAL
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            provider=provider,
            input_schema=data.get("input_schema") or {},
            output_schema=data.get("output_schema") or {},
            tags=list(data.get("tags") or []),
            version=data.get("version", "0.1.0"),
            enabled=bool(data.get("enabled", True)),
            risk=data.get("risk", "low"),
            timeout=data.get("timeout"),
            config=data.get("config") or {},
            metadata=data.get("metadata") or {},
        )


@dataclass
class ToolResult:
    """Result of tool execution."""

    tool_name: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolExecutionContext:
    """Context for tool execution."""

    tool_name: str
    parameters: Dict[str, Any]
    hemisphere: str
    confidence: float = 0.5
    expected_success: bool = True
    bullets_used: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolExecutionRecord:
    """Execution record with context and steps."""

    context: ToolExecutionContext
    result: ToolResult
    timestamp: datetime = field(default_factory=datetime.utcnow)
    execution_steps: List[Dict[str, Any]] = field(default_factory=list)
