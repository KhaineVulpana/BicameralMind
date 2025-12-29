# Knowledge RAG usage

Use RAG for durable reference material and facts. Do not store procedures
or action checklists in RAG. Those belong in procedural memory.

Recommended seed sources:
- Architecture summaries and conventions.
- Key workflows and terminology.
- Tooling policies, safety rules, and access limits.

Defaults:
- retrieval_mode: agentic
- top_k: 5
- max_iterations: 5

If the RAG store is small, agentic iteration is skipped to save time.
You can override the threshold with rag.min_docs_for_agentic in config.
