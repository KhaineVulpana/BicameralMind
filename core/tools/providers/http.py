"""Provider for HTTP tools."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

import aiohttp
from loguru import logger

from ..models import ToolDefinition, ToolResult
from .base import ToolProviderBase


class HTTPToolProvider(ToolProviderBase):
    """Executes HTTP requests based on tool config."""

    async def execute(
        self,
        tool: ToolDefinition,
        params: Dict[str, Any],
        timeout: Optional[float] = None,
    ) -> ToolResult:
        cfg = tool.config or {}
        method = (cfg.get("method") or "GET").upper()
        url = cfg.get("url")
        if not url:
            return ToolResult(
                tool_name=tool.name,
                success=False,
                error="Missing url in tool config",
            )

        headers = self._render_mapping(cfg.get("headers") or {}, params)
        query = self._render_mapping(cfg.get("query_params") or {}, params)
        body = cfg.get("body")
        json_body = None
        data_body = None
        if isinstance(body, dict):
            json_body = self._render_mapping(body, params)
        elif isinstance(body, str):
            data_body = self._render_text(body, params)

        logger.debug(f"HTTP tool: {tool.name} -> {method} {url}")

        session_timeout = aiohttp.ClientTimeout(total=timeout) if timeout else None
        try:
            async with aiohttp.ClientSession(timeout=session_timeout) as session:
                async with session.request(
                    method,
                    url,
                    headers=headers,
                    params=query or None,
                    json=json_body,
                    data=data_body,
                ) as resp:
                    text = await resp.text()
                    success = 200 <= resp.status < 300
                    output = self._maybe_json(text)
                    return ToolResult(
                        tool_name=tool.name,
                        success=success,
                        output=output,
                        error=None if success else f"HTTP {resp.status}",
                        metadata={"status": resp.status},
                    )
        except Exception as exc:
            return ToolResult(
                tool_name=tool.name,
                success=False,
                error=str(exc),
            )

    @staticmethod
    def _render_text(template: str, params: Dict[str, Any]) -> str:
        rendered = template
        for key, val in params.items():
            rendered = rendered.replace(f"{{{key}}}", str(val))
        return rendered

    def _render_mapping(self, mapping: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        rendered: Dict[str, Any] = {}
        for key, val in mapping.items():
            if isinstance(val, str):
                rendered[key] = self._render_text(val, params)
            else:
                rendered[key] = val
        return rendered

    @staticmethod
    def _maybe_json(text: str) -> Any:
        try:
            return json.loads(text)
        except Exception:
            return text
