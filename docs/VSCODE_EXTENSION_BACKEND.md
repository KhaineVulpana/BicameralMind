# VS Code Extension Backend (BicameralMind Desktop Service)

This document describes the backend requirements to support a VS Code extension (client-owned projects, backend-owned knowledge) for a single user on a LAN/VPN.

## Goals
- Provide a stable, versioned network API the VS Code extension can call.
- Stream responses (Claude/Codex-like).
- Return a clean separation between:
  - `final`: user-facing answer
  - `details`: hemisphere traces, RAG traces, tool traces, retrieved bullets
- Support “backend proposes tools, extension executes locally” (safer for client-owned workspaces).

## Non-Goals (for now)
- Multi-user identity/permissions.
- Server-side workspace checkout and direct file edits.
- Internet-exposed deployment.

## Runtime / Deployment
- **Bind address**: configurable host/port (e.g. `0.0.0.0:8000`) for LAN access.
- **TLS**: run behind a local reverse proxy (Caddy recommended) to expose `https://<desktop-host>`.
- **Firewall**: allow only LAN/VPN subnets.

## Authentication
Single-user API token:
- Require `Authorization: Bearer <token>` on all `/v1/*` endpoints.
- Store token in `config/config.yaml` (rotatable), or load from environment.

## Namespacing (single user, many projects/devices)
Even with a single user, the backend should accept:
- `project_id`: stable id per VS Code workspace (extension-managed).
- `device_id`: stable id for the desktop service (configured once).

Backend persists data partitioned by `{project_id}` (and optionally `{device_id}` for device-tier).

## Core API (v1)

### Models
- `GET /v1/models/ollama`
  - Returns locally available models from `ollama list`.
- `GET /v1/models/active?project_id=...`
  - Returns active `slow` and optional `fast`.
- `POST /v1/models/active`
  - Body: `{ project_id, slow, fast? }`
  - Persists and updates runtime.

### Sessions / Chat
- `POST /v1/sessions`
  - Body: `{ project_id, metadata? }`
  - Returns: `{ session_id }`
- `POST /v1/sessions/{session_id}/messages`
  - Body: `{ text, mode?, temperature?, max_tokens?, client_context? }`
  - Returns (non-stream fallback): `{ message_id, final, details }`
- `GET /v1/sessions/{session_id}/events` (SSE)
  - Streams: `token`, `final`, `details`, `tool_call`, `error`

### Tool loop (backend proposes, extension executes)
- `tool_call` SSE event payload:
  - `{ tool_call_id, name, args, risk, requires_confirmation }`
- `POST /v1/tool_results`
  - Body: `{ session_id, tool_call_id, success, output, artifacts? }`
  - Backend uses this to continue synthesis and (optionally) learn outcomes.

### Knowledge ingestion (optional, phase 2)
For RAG docs and long-lived notes:
- `POST /v1/knowledge/documents`
  - Body: `{ project_id, tier, documents: [{text, source, metadata?}] }`

## Response Shape
Minimum stable schema:
```json
{
  "message_id": "msg_...",
  "final": "string",
  "details": {
    "left": "string",
    "right": "string",
    "rag_context": { "answer": "string", "sources": ["..."], "iterations": 2 },
    "retrieved_bullets": [
      { "id":"...", "text":"...", "side":"left", "score":0.8, "tags":["..."] }
    ],
    "tool_trace": [ { "tool":"...", "success":true, "duration_ms": 123 } ]
  }
}
```

## Config Additions (recommended)
- `server.host`, `server.port`
- `server.auth_token`
- `server.cors_allowed_origins` (allow only VS Code webview origin patterns)
- `storage.root` (absolute)
- `storage.partition_by_project: true`

## TODO Checklist
- [ ] Add `/v1/*` API surface (keep current UI endpoints as legacy/internal).
- [ ] Add auth middleware for `/v1/*`.
- [ ] Add SSE streaming for chat + tool loop.
- [ ] Add project namespacing for all persisted stores.
- [ ] Add tool proposal/result loop contracts (no direct server-side file edits for VS Code mode).
- [ ] Add structured `details` fields (versioned) and keep them stable.
- [ ] Add deployment guide for Caddy + Windows firewall rules.

