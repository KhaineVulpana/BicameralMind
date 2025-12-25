# Procedure Cheatsheets Plan

Last Updated: December 24, 2025

## Goal
Create a structured store for multi-step procedures (cheatsheets) that chain procedural bullets into repeatable playbooks. These should be searchable, auditable, and usable by the UI and the agents.

## Core Concepts
- A procedure is a named, multi-step playbook.
- Steps can reference existing bullet IDs, raw step text, or tool calls.
- Procedures can be tagged, versioned, and scoped to a hemisphere or shared.
- Procedures should not replace bullets; they should compose bullets.

## Data Model (Draft)
```
Procedure:
  id: "proc_<timestamp>_<shortid>"
  title: "Tool invocation checklist"
  description: "Safe sequence for running tools and logging outcomes"
  side: "left" | "right" | "shared"
  tags: ["mcp", "tooling", "safety"]
  steps:
    - type: "bullet"
      ref_id: "pb_left_123"
    - type: "text"
      text: "Validate inputs before calling tool"
    - type: "tool"
      tool_name: "filesystem.read_file"
      params_template: "{path}"
  status: "active" | "draft" | "deprecated"
  helpful_count: 0
  harmful_count: 0
  created_at: "..."
  updated_at: "..."
  source_trace_id: "..."
```

## Storage
- Start with JSONL file: `data/memory/procedures.jsonl`
- Optional: migrate to SQLite for richer queries and versioning.
- Keep storage separate from procedural bullet vector store.

## Retrieval
- Search by title, tags, and side.
- Optional: embed procedure title + description for semantic search.
- Allow filtering by status and tag.

## API (Draft)
- `GET /api/procedures?side=shared&limit=50`
- `POST /api/procedures` (create)
- `PATCH /api/procedures/{id}` (edit/activate/deprecate)
- `DELETE /api/procedures/{id}` (remove)

## UI (Dashboard)
- List procedures with tags, side, and score.
- Search and filter by hemisphere and tag.
- Detail view showing steps and referenced bullet IDs.
- Promote a draft to active after validation.

## Learning Integration
- Procedures can be suggested by the learning pipeline after repeated bullet sequences.
- Outcome-based scoring should mirror bullet scoring rules.
- A procedure can be promoted to shared only after multi-run success.

## Implementation Steps
1. Add `core/memory/procedure_store.py` to manage CRUD and persistence.
2. Add new API endpoints in `api/main.py` for list/create/update/delete.
3. Add a procedures panel to the Dashboard tab with list + detail.
4. Add minimal tests for CRUD and search.
5. Wire optional semantic search once stable.

## Notes
- Keep procedures strictly additive; do not overwrite bullet text.
- Allow referencing both shared and hemisphere-specific bullets.
- Keep the initial implementation simple; iterate after usage feedback.
