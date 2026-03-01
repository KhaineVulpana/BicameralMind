# VS Code Extension TODO (Single-User, Client-Owned Projects)

This TODO list tracks everything needed to ship a VS Code extension that connects to a BicameralMind desktop backend over the network, with a Claude/Codex-like chat UX plus an optional “Trace” tab for hemisphere/RAG/tool details.

Related docs:
- `docs/VSCODE_EXTENSION_BACKEND.md`
- `docs/VSCODE_EXTENSION_FRONTEND.md`

---

## Milestone 0: Decisions (lock before coding)
- [ ] Confirm transport: **SSE** for streaming (recommended) vs WebSocket
- [ ] Confirm auth: **single static bearer token** (initially)
- [ ] Confirm scoping: `project_id` generated per workspace; backend stores knowledge per project
- [ ] Confirm tool loop: backend proposes → extension executes locally (default)

---

## Milestone 1: Backend “v1” API (MVP)

### Versioning + Auth
- [ ] Add `/v1/*` routes (don’t reuse legacy UI endpoints for the extension)
- [ ] Require `Authorization: Bearer <token>` for `/v1/*`
- [ ] Add `server.auth_token` to `config/config.yaml` (and/or env override)

### Sessions + Chat (non-stream)
- [ ] `POST /v1/sessions` → `{session_id}`
- [ ] `POST /v1/sessions/{session_id}/messages`
  - Request: `{ project_id, text, mode?, temperature?, max_tokens?, client_context? }`
  - Response: `{ message_id, final, details }`
- [ ] Include stable `details` schema:
  - [ ] `details.left`, `details.right`
  - [ ] `details.rag_context` (answer, sources, iterations)
  - [ ] `details.retrieved_bullets`
  - [ ] `details.tool_trace` (if tools executed)

### Models
- [ ] `GET /v1/models/ollama`
- [ ] `GET /v1/models/active?project_id=...`
- [ ] `POST /v1/models/active` body: `{ project_id, slow, fast? }`

**Acceptance**
- [ ] Curl/Postman can create a session and send a message and receive `final` + `details`
- [ ] `details` fields remain stable across releases (versioned)

---

## Milestone 2: Backend Streaming (Claude/Codex-like)
- [ ] Implement SSE endpoint:
  - [ ] `GET /v1/sessions/{session_id}/events` (stream)
  - Events: `token`, `final`, `details`, `tool_call`, `error`
- [ ] Add cancellation:
  - [ ] `POST /v1/sessions/{session_id}/cancel` (or `DELETE /.../stream`)

**Acceptance**
- [ ] VS Code can render token-by-token output reliably with reconnect behavior

---

## Milestone 3: Tool Loop Contract (Backend proposes → Extension executes)

### Backend tool calls
- [ ] Define tool call payload:
  - `{ tool_call_id, name, args, risk, requires_confirmation }`
- [ ] Emit `tool_call` SSE events when the backend wants a local tool run
- [ ] Add endpoint for tool results:
  - [ ] `POST /v1/tool_results` body: `{ session_id, tool_call_id, success, output, artifacts? }`

### Safety
- [ ] Default deny: backend cannot request high-risk tools unless explicitly enabled
- [ ] Add audit logging (tool proposals + confirmations + outcomes)

**Acceptance**
- [ ] Backend can request a “read/search” tool and incorporate result into the answer
- [ ] High-risk execution requires explicit confirmation in the extension UI

---

## Milestone 4: VS Code Extension Skeleton (UI + non-stream chat)

### Extension scaffolding
- [ ] New `vscode-extension/` package (TypeScript)
- [ ] `package.json` contributions:
  - [ ] view container + view (sidebar)
  - [ ] commands: open panel, clear session, reconnect
  - [ ] settings: backend URL, auth token, model defaults

### Project identity
- [ ] Create `project_id` per workspace (persist in `.vscode/` or global state)
- [ ] Send `project_id` on every request

### Webview UI
- [ ] Chat transcript + composer
- [ ] Mode selector (auto/left/right)
- [ ] Model selectors (slow/fast)
- [ ] “Trace” tab/panel that renders `details` (collapsed by default)

**Acceptance**
- [ ] Non-stream `POST /v1/.../messages` works from VS Code
- [ ] Trace panel shows left/right/RAG and retrieved bullets cleanly

---

## Milestone 5: VS Code Streaming Client
- [ ] Implement SSE client in extension host
- [ ] Stream tokens to webview incrementally
- [ ] Add stop/cancel button
- [ ] Reconnect strategy (exponential backoff; resume session)

**Acceptance**
- [ ] Streaming output feels comparable to Claude/Codex
- [ ] Trace updates can arrive after `final` without breaking UI

---

## Milestone 6: Local Tool Execution (MVP)

### Read/search tools (low risk)
- [ ] `workspace.readFile`
- [ ] `workspace.listFiles` / glob
- [ ] `workspace.search` (ripgrep via VS Code search API if possible)
- [ ] `git.status`, `git.diff` (VS Code Git API preferred)

### Apply edits (medium risk)
- [ ] Diff preview UI
- [ ] `workspace.applyEdit` / text edits
- [ ] Return structured “applied edits” artifacts to backend

### Terminal execution (high risk, off by default)
- [ ] Explicit per-call confirmation
- [ ] Output capture + truncation

**Acceptance**
- [ ] Backend can request file context and propose an edit; user can approve; changes apply in workspace

---

## Milestone 7: Knowledge Scoping (Project-tier first)
- [ ] Backend persists knowledge per `project_id`
- [ ] Optional: add “universal vs device vs project” tiers later (explicitly opt-in)

---

## Milestone 8: Packaging + Release
- [ ] Dev: local backend URL support + self-signed TLS notes
- [ ] Production: recommend TLS via Caddy + LAN firewall configuration
- [ ] Publish extension (private vs marketplace)

---

## Nice-to-haves (later)
- [ ] “Explain” mode: highlight which bullets/sources influenced the final answer
- [ ] Tool policy editor in VS Code settings UI
- [ ] Conversation export/import per workspace
- [ ] Multi-device sync of universal tier knowledge

