# Fast/Slow LLM Split

This project can be configured to use two different LLMs:

- **fast**: low-latency model for short “inner loop” calls (e.g., RAG coverage checks, query refinement)
- **slow**: higher-quality model for user-facing synthesis (final answers)

## Default Behavior

If you do not configure a separate fast model, the system uses the same model for both fast and slow calls.

## Configuration

Edit `config/config.yaml`:

```yaml
model:
  slow:
    name: qwen3:14b
    temperature: 0.7
  fast:
    name: qwen2.5:3b
    temperature: 0.2
```

You can also keep the legacy shape:

```yaml
model:
  name: qwen3:14b
  temperature: 0.7
```

## Current Routing

- `integrations/rag/agentic_rag.py`
  - coverage + query refinement use **fast**
  - final synthesis uses **slow**

## Notes

- If both models cannot stay resident in VRAM, switching between them may introduce extra latency (model load/unload).
- Reducing the number of LLM calls (e.g., using `rag.retrieval_mode: single` or lowering `rag.max_iterations`) is often the biggest speed win.

