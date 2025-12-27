# RAG ↔ Procedural Memory Notes (Design Discussion)

This document captures a design discussion about how (or whether) to connect:

- **RAG**: retrieved, document-sourced knowledge (Chroma vector store in `integrations/rag/agentic_rag.py`)
- **Procedural memory**: outcome-scored ACE-style bullets persisted via Chroma in `core/memory/procedural_store.py`

No changes described here are implemented yet; this is a planning artifact.

## Current Behavior (As Implemented)

- `AgenticRAG` creates a Chroma vector store handle, but it starts **empty** unless something calls `AgenticRAG.add_documents(...)` (or there is persisted data already on disk).
- The UI/chat path does **not** ingest any baseline corpus into the RAG store.
- In the chat path (`core/bicameral_mind.py`):
  - RAG retrieval runs (when enabled) to produce `rag_context`.
  - `rag_context` is not currently injected into hemisphere prompts; hemispheres read `content["input"]` and ignore `content["rag_context"]`.
- Procedural memory is a separate system:
  - It is designed to store **small procedural bullets** (rules/checklists/pitfalls/templates).
  - It is **outcome-based** (helpful/harmful counts), and the Curator is intended to be the only writer.
  - It is already integrated with tool execution learning paths (MCP traces), but not with chat responses.

## Why Keep RAG and Procedural Memory Separate

The codebase currently encodes a separation-of-concerns:

- RAG is "what the docs say" (may be stale, conflicting, or context-specific).
- Procedural memory is "what has repeatedly worked for this system" (scored, curated, promoted over time).

This separation reduces the risk of freezing unverified or volatile facts into durable procedures.

## When Feeding RAG → Procedural Memory Is Helpful

Examples:

- A retrieved runbook procedure is used in execution and repeatedly succeeds (tool success, tests pass, user confirms).
- Stable internal conventions are retrieved (repo-specific workflows, required formats) and validated by outcomes.
- RAG retrieves tool usage instructions that become reliable playbooks after verification.

## When Feeding RAG → Procedural Memory Is Harmful

Examples:

- RAG sources change frequently (release notes, endpoints, feature flags) and procedures become stale.
- RAG is context-specific (OS, environment, repo) but is promoted as general guidance.
- Conflicting sources lead to a brittle "chosen" procedure without awareness of uncertainty.
- Adversarial/low-quality content gets retrieved and becomes a durable behavior.

## Key Distinction: "RAG Step" vs "Procedural Bullet"

They can look similar (both may contain steps), but differ by:

- **Provenance**: docs vs learned.
- **Trust**: retrieved vs outcome-gated.
- **Context**: raw snippet vs preconditions/when-to-apply.
- **Lifecycle**: mutable docs vs quarantined→active→shared promotion.

Example transformation:

- RAG: "Restart service X, then clear cache Y."
- Procedural bullet: "If service X returns 502 after deploy, restart X then clear cache Y; validated 4/4 times in env=prod; avoid if X is in migration."

## Proposed Future Approach: Two-Sided Proposal + Verification

Goal: allow RAG-derived procedures without contaminating procedural memory.

High-level flow:

1. **Right hemisphere (generator)** drafts candidate procedural bullets from RAG sources:
   - include preconditions, steps, expected outcome, failure modes, and source citations.
2. **Left hemisphere (reflector/critic)** challenges and normalizes:
   - checks for ambiguity, missing constraints, safety issues, contradictions with existing bullets.
   - requires an explicit verification plan.
3. **Curator (writer/policy enforcer)** stages the candidate:
   - store in `staging` with metadata: `origin="rag"`, `sources=[...]`, `requires_outcome=true`.
   - do not promote to active/shared until a real outcome signal is observed.

Important note: LLM-vs-LLM verification is not sufficient by itself; promotion should remain outcome-gated.

## Meta-Controller Role (Gating, Not Writing)

Discussion takeaway:

- The meta-controller is best used to decide **when** to run heavier reflection/curation work (tick-gated),
  not as the component that directly writes procedural memory.
- Keeping `Reflector`/`Curator` as explicit modules maintains hygiene rules (quarantine, promotion thresholds, dedup).

## Open Implementation Questions

- What counts as an "outcome signal" for chat-derived procedures?
  - explicit user confirmation, user correction, downstream tool success/failure, test results, validator checks.
- How should RAG sources be represented for citations and re-validation (file path, doc id, hash, timestamp)?
- Should RAG-derived procedures have TTL / expiry (especially for volatile sources)?
- How to prevent overfitting: ensure procedures include "when NOT to apply" and environment scoping metadata.

