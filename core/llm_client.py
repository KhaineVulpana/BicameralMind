"""LLM client wrapper for tests and integrations."""
from __future__ import annotations

from typing import Any, Dict

try:
    from langchain_ollama import OllamaLLM as Ollama
except ImportError:
    # Fallback to old import for compatibility
    from langchain_community.llms import Ollama


class LLMClient(Ollama):
    """Thin wrapper around Ollama to standardize config loading."""

    def __init__(self, config: Dict[str, Any] | None = None):
        model_config = (config or {}).get("model", {})
        super().__init__(
            model=model_config.get("name", "qwen2.5:14b"),
            temperature=model_config.get("temperature", 0.7),
            base_url=model_config.get("base_url"),
        ) 