# BicameralMind system overview

This system is a bicameral architecture with two agent styles and a meta-controller.
Use it for structured reasoning and exploration while keeping factual RAG separate
from procedural memory.

Core components:
- Left brain: pattern recognition, validation, replication.
- Right brain: exploration, mutation, novelty.
- Meta-controller: selects mode (exploit, explore, integrate) and manages tick rate.
- Procedural memory: bullet-based rules learned from outcomes.
- Knowledge RAG: document store for facts, docs, references.
- Tools: local, CLI, HTTP, or MCP providers.

UI entry points:
- Chat tab: send messages, set mode, pick models.
- Tools tab: view tools, run tools, manage MCP servers.
- Staging tab: review candidate procedural bullets.

Key separation:
- RAG is for "what the docs say".
- Procedural memory is for "what we have learned works".
