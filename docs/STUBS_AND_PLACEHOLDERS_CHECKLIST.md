# Stubs, Placeholders, and Mock Systems (Checklist)

This checklist tracks UI elements and backend systems that are currently static, mocked, or explicitly marked as TODO/stub/placeholder.

Scope: project code under `core/`, `api/`, `integrations/`, `static/`, plus “Remaining TODOs” callouts in design docs.

## UI / Frontend

### Tools Tab: Analytics (static)
- [x] Replace hardcoded “Tool Analytics” cards with real stats from backend (success rate, most used, most learning).
  - Ref: `static/index.html:483` (“Tool Analytics” section).
- [x] Replace the hardcoded “Success Rate Timeline” bar chart with real data.
  - Ref: `static/index.html:505` (inline `<span style="height: ...">` bars).
- [x] Add an API endpoint to return tool execution stats/time series (or expose `ToolExecutor.get_stats()` + history summaries) and render it.
  - Ref: `core/tools/executor.py` (`execution_history`, `get_stats()`).

### Tools Tab: Tool Flow (placeholder)
- [x] Implement “Tool Flow” visualization instead of the placeholder nodes.
  - Ref: `static/index.html:521` (“Visual execution chains (placeholder).”)
  - Ref: `static/index.html:524` (`.flow-placeholder` nodes).
  - Possible data source: tool execution history + (future) structured tool traces.

### Tools Tab: Tool Search (not wired)
- [x] Wire `#tool-search` input to filter tools in the registry list.
  - Ref: `static/index.html:462` (search input exists).
  - Note: procedures search is wired; tools search is not.

### Chat Sidebar: Retrieved Bullets (not wired)
- [x] Populate `#chat-context` with real retrieved procedural bullets (IDs + text + score) used for the current response.
  - Ref: `static/index.html:360` (`#chat-context` exists).
  - Backend data source options:
    - return `bullets_used` IDs + bullet text in `/api/chat/message` response
    - or add a dedicated endpoint for “last chat trace”.

### MCP “Advanced Config” (broken linkage)
- [x] Make `openMCPConfig()` available from the main UI page, or change the button to open the dedicated config page explicitly.
  - Ref: `static/index.html:397` (button calls `openMCPConfig()`).
  - Ref: `static/mcp-config.html:315` (function exists only inside that HTML file).

## Backend / API

### MCP Server Tool Count (stubbed)
- [x] Return real `tools` count per server in `/api/mcp/servers` instead of hardcoding `0`.
  - Ref: `api/main.py:897` (`"tools": 0,  # TODO: Get actual tool count`).
  - Options:
    - count tools from `mcp_client` per server (if connected)
    - track last-discovered count during MCP tool registration

### “TEST MODE” fallback behavior (real but important)
- [x] Decide how UI should present/limit functionality in test mode (BicameralMind not initialized).
  - Ref: `api/main.py:713` (`[TEST MODE]` response).
  - Ref: `api/main.py:29` / `api/main.py:91` (startup fallback logs).

## MCP Integration (Mocks / Fallbacks)

### Mock tools fallback
- [x] Decide whether MCP mock fallback should exist in production; if not, disable/remove it.
  - Ref: `integrations/mcp/mcp_client.py:204` (“Falling back to mock tools…”).
- [x] Replace `_get_mock_tools()` with real tool discovery / schema normalization, or limit it to unit tests.
  - Ref: `integrations/mcp/mcp_client.py:318` (“will be replaced with real discovery”).

### MCP server package/config issues (operational)
- [x] Fix/verify MCP server packages referenced in `config/config.yaml` (e.g., the PowerShell MCP server package name).
  - Symptom: npm 404 on `@executeautomation/powershell-mcp-server` during startup.
  - Ref: `config/config.yaml` (`mcp.servers`).

## Procedural Memory / Learning Pipeline

### Pruning + Dedup wiring (high-level API stubs)
- [x] Wire `ProceduralMemory.prune_low_quality()` to `core/memory/pruner.py` (or remove stub method).
  - Ref: `core/memory/procedural_memory.py:407` (“Pruning not yet implemented”).
  - Implementation exists: `core/memory/pruner.py`.
- [x] Wire `ProceduralMemory.deduplicate()` to `core/memory/deduplicator.py` (or remove stub method).
  - Ref: `core/memory/procedural_memory.py:416` (“Deduplication not yet implemented”).
  - Implementation exists: `core/memory/deduplicator.py`.

### Curator maintenance methods are stubs
- [x] Replace `Curator.prune_low_quality()` stub with calls into `Pruner` (respecting dry-run, backups, policy).
  - Ref: `core/memory/curator.py:413` (“Implement actual pruning logic”).
- [x] Replace `Curator.deduplicate()` stub with calls into `Deduplicator` / `BulletMerger`.
  - Ref: `core/memory/curator.py:449` (“Implement actual deduplication logic”).

### Retrieval utilities: “recent” and “controversial” are stubs
- [x] Implement `MemoryRetriever.retrieve_recent()` (time-based list, possibly from metadata timestamps).
  - Ref: `core/memory/retrieval.py:263`.
- [x] Implement `MemoryRetriever.retrieve_controversial()` (bullets with both helpful and harmful signals).
  - Ref: `core/memory/retrieval.py:277`.

### Other Curator TODOs (quality + stats)
- [x] Improve `Curator._is_duplicate()` accuracy (embedding similarity vs text heuristics).
  - Ref: `core/memory/curator.py:271`.
- [x] Add status filtering support in retrieval/list paths for curator workflows.
  - Ref: `core/memory/curator.py:536`.
- [x] Add richer curation stats (by type/status, promotion/deprecation rates).
  - Ref: `core/memory/curator.py:553`.

### Deduplicator placeholder helper
- [x] Decide whether to remove/keep the “simple embedding fallback” (`_text_to_simple_embedding`) and ensure it’s never used in production paths.
  - Ref: `core/memory/deduplicator.py:260`.

## Docs Mentioning “Remaining TODOs” (Cross-check)

These docs contain their own “Remaining TODOs” lists; keep them aligned with the code checklist above.

- [x] Reconcile `docs/PHASE2_LEARNING_PIPELINE.md` “Remaining TODOs” with current code status (some items may already be implemented).
  - Ref: `docs/PHASE2_LEARNING_PIPELINE.md` (section “### Remaining TODOs:”).
- [x] Reconcile `docs/PROCEDURAL_MEMORY_IMPLEMENTATION.md` “Remaining TODOs” with current code status.
  - Ref: `docs/PROCEDURAL_MEMORY_IMPLEMENTATION.md` (section “### Remaining TODOs:”).
