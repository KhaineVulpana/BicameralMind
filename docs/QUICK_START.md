# Quick Start Guide - Bicameral Mind Procedural Memory

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Key dependencies:
- `chromadb` - Vector database for procedural memory
- `sentence-transformers` - Embeddings
- `langchain` - LLM framework
- `rich` - Pretty console output
- `pydantic` - Data validation

### 2. Install Ollama (for local LLM)

Download from: https://ollama.ai

Pull a model:
```bash
ollama pull qwen3:14b
```

## Running Examples

### Test Procedural Memory

```bash
python tests/test_procedural_memory.py
```

This runs a test suite that verifies:
- Basic CRUD operations
- Bullet dataclass functionality
- Hemisphere separation

### Comprehensive Examples

```bash
python examples/procedural_memory_example.py
```

Demonstrates:
- Adding bullets to left/right brains
- Retrieving relevant bullets
- Outcome-based learning
- Automatic promotion to shared memory
- Advanced retrieval patterns

### Interactive Mode

```bash
python main.py
```

Commands:
- Type your queries naturally
- `/status` - View consciousness state
- `/history` - View conversation history
- `/quit` - Exit

## Quick Usage Example

```python
from core.memory import ProceduralMemory, Bullet, BulletType, Hemisphere

# Initialize
config = {
    "procedural_memory": {
        "enabled": True,
        "persist_directory": "./data/memory/procedural",
    }
}
memory = ProceduralMemory(config)

# Add knowledge
bullet = memory.add(
    text="Always validate inputs before processing",
    side=Hemisphere.LEFT,
    bullet_type=BulletType.HEURISTIC,
    tags=["validation", "best-practice"],
)

# Retrieve relevant knowledge
bullets, ids = memory.retrieve(
    query="input validation",
    side=Hemisphere.LEFT,
    k=5,
)

# Record outcome (tool succeeded)
memory.record_outcome(ids, helpful=True)

# Check stats
stats = memory.get_stats()
print(f"Left brain: {stats['collections']['left']['count']} bullets")
```

## Configuration

Edit `config/config.yaml`:

```yaml
# Model settings
model:
  name: "qwen3:14b"  # Your Ollama model
  temperature: 0.7

# Procedural memory (ACE-style)
procedural_memory:
  enabled: true
  persist_directory: "./data/memory/procedural"
  embedding_model: "sentence-transformers/all-MiniLM-L6-v2"

  # Learning thresholds
  promote_threshold: 3      # Helpful count needed for shared promotion
  quarantine_threshold: 2   # Helpful count to activate quarantined bullets

  # Retrieval settings
  k_left: 8    # Left brain: fewer, higher-confidence bullets
  k_right: 16  # Right brain: more, exploratory bullets
  k_shared: 5  # Shared memory bullets per query

# RAG (optional, separate from procedural memory)
rag:
  enabled: false

# Left brain config
left_brain:
  confidence_threshold: 0.6  # Pattern matching threshold

# Right brain config
right_brain:
  confidence_threshold: 0.4  # Exploration threshold (lower)
```

## Project Structure

```
BicameralMind/
 core/
    memory/                    #  NEW: Procedural Memory System
       __init__.py
       bullet.py             # Bullet dataclass + enums
       procedural_store.py   # Low-level Chroma interface
       procedural_memory.py  # High-level API
       retrieval.py          # Advanced retrieval
    left_brain/
       agent.py              #  Updated
    right_brain/
       agent.py              #  Updated
    meta_controller/
    bicameral_mind.py         #  Updated
    base_agent.py
 examples/
    procedural_memory_example.py  #  NEW
    usage.py
 docs/
    PROCEDURAL_MEMORY_IMPLEMENTATION.md  #  NEW
    QUICK_START.md                       #  NEW (this file)
    Bicameral_Mind_Handoff.md
    Bicameral_Mind_Checklist.md
 tests/test_procedural_memory.py     #  NEW
 main.py
 requirements.txt
 config/
     config.yaml
```

## Key Concepts

### 1. Bullets vs RAG
- **Procedural Memory (Bullets)**: "How to do things" - strategies, heuristics, tool rules
- **RAG**: "What things are" - facts, documents, reference material

**Keep them separate!**

### 2. Three Collections
- `procedural_left` - Left brain's knowledge (pattern continuity)
- `procedural_right` - Right brain's knowledge (exploration)
- `procedural_shared` - Consensus knowledge (promoted from left/right)

### 3. Outcome-Based Learning
Bullets are scored based on **actual outcomes**, NOT time or ticks:
-  Tool succeeded -> `helpful=True`
-  Tool failed -> `helpful=False`
-  Test passed -> `helpful=True`
-  Test failed -> `helpful=False`

### 4. Automatic Lifecycle
```
NEW BULLET (quarantined)
     (helpful_count >= 2, harmful_count == 0)
ACTIVE
     (helpful_count >= 3, harmful_count == 0)
PROMOTED TO SHARED
```

## Troubleshooting

### Import Errors
If you get `ModuleNotFoundError`:
```bash
pip install -r requirements.txt
```

### Ollama Connection Error
Make sure Ollama is running:
```bash
ollama serve
```

### Vector DB Issues
Delete and recreate:
```bash
rm -rf ./data/memory/procedural
```

Then restart your script.

### Type Errors
Make sure you're using the enums:
```python
#  Correct
side=Hemisphere.LEFT
bullet_type=BulletType.HEURISTIC

#  Wrong
side="left"  # Use enum!
bullet_type="heuristic"  # Use enum!
```

## Next Steps

1. **Run the examples** to understand the system
2. **Add your own bullets** for your use case
3. **Integrate with your agents** for outcome-based learning
4. **Monitor promotion** to shared memory
5. **Implement reflection module** (Phase 2)

## Resources

- [Implementation Docs](PROCEDURAL_MEMORY_IMPLEMENTATION.md) - Complete technical details
- [Handoff Doc](Bicameral_Mind_Handoff.md) - Design philosophy
- [ACE Paper](study.pdf) - Research foundation
- [Examples](../examples/procedural_memory_example.py) - Usage examples

---

**Status:**  Phase 1 Complete

**What Works:**
-  Bullet-based storage
-  Three-collection architecture
-  Outcome-based learning
-  Automatic promotion
-  Per-hemisphere retrieval
-  Advanced retrieval patterns
-  Integration with agents

**Coming in Phase 2:**
- Reflection module
- Curator logic
- Deduplication
- Pruning
- Tick-gated reflection depth
- MCP integration for tool outcomes

---

Need help? Check the examples or read the full implementation docs!
