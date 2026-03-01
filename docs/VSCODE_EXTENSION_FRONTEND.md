# VS Code Extension Frontend (Client)

This document describes the VS Code extension that connects to a BicameralMind desktop backend over the network, while keeping project files local to the developer’s machine.

## UX Goals
- A chat experience similar to Claude/Codex in VS Code:
  - streaming assistant output
  - persistent conversation per workspace
  - quick commands (slash commands) and tool confirmations
- A dedicated “Trace” view/tab to inspect:
  - left/right hemisphere outputs
  - RAG iteration traces and sources
  - retrieved bullets
  - tool execution traces

## Architecture Overview
- **Extension Host (Node)**:
  - Owns auth token storage and backend URL settings.
  - Manages SSE/WebSocket connection.
  - Executes local tools (workspace reads/edits, terminal commands) after user confirmation.
- **Webview UI**:
  - Renders chat transcript + streaming output.
  - Renders Trace panel (toggle/tab).
  - Provides model pickers (slow/fast) and mode controls.

## Project Identity
Single user, many projects:
- Generate a stable `project_id` per workspace (store in `.vscode/bicameralmind.json` or globalState keyed by workspace URI).
- Send `project_id` with every request.

## Security Model (recommended)
- Backend never edits files directly in VS Code mode.
- Backend proposes tool calls; extension confirms and executes.
- Maintain allowlist of local tools enabled by the user.

## Local Tools (MVP)
**Read-only / low-risk**
- `workspace.readFile(path)`
- `workspace.search(query, include/exclude globs)`
- `workspace.listFiles(glob)`
- `git.status`, `git.diff` (via VS Code Git API or shell)

**Write / medium-risk (requires confirmation)**
- `workspace.applyEdits([{path, diff}])` (show diff preview UI)

**High-risk (off by default)**
- `terminal.run(command)` (explicit confirmation each time)

## UI Layout
- **Chat view** (default):
  - Message list
  - Composer input
  - Model dropdowns (slow/fast)
  - Mode selector (auto/left/right)
- **Trace view/tab**:
  - Collapsible sections: RAG, Left, Right
  - Retrieved bullets list (id, score, side, tags)
  - Tool trace list (tool name, duration, success)

## Network Protocol
- Prefer **SSE** for streaming:
  - reconnect logic on disconnect
  - incremental token rendering
  - handle `tool_call` events mid-stream
- Fallback:
  - non-stream `POST /v1/sessions/{id}/messages`

## Implementation Plan

### Phase 1: Skeleton + non-stream chat
- Create extension scaffolding (TypeScript, webview).
- Add settings:
  - backend URL
  - auth token
- Implement session creation and non-stream send/receive.
- Render `final` output and a basic Trace panel from `details`.

### Phase 2: Streaming + trace fidelity
- Implement SSE client with event parsing.
- Add streaming rendering + cancellation.
- Add more trace rendering: retrieved bullets, tool trace.

### Phase 3: Local tool execution loop
- Implement tool proposal handling:
  - show confirmation modal
  - run tool locally
  - send `tool_results` back to backend
- Add allowlist + risk gating.

### Phase 4: Polishing
- Conversation history persistence per workspace.
- Better UX: slash commands, context selectors, diff preview workflow.
- Telemetry/logging (local-only).

## TODO Checklist
- [ ] `package.json` contributes: view container, commands, settings.
- [ ] Webview UI (chat + trace tab).
- [ ] Backend client: auth header, retries, timeouts.
- [ ] Session management (`project_id`, session id storage).
- [ ] Streaming SSE implementation.
- [ ] Tool-call UI + confirmations.
- [ ] Local tool runners (read/search/apply edits).
- [ ] Diff preview for edits.
- [ ] Error handling (offline backend, auth failures).

