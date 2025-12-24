# Procedural Memory System - Implementation Complete ✅

## Overview

The **Procedural Memory System** for Bicameral Mind has been successfully implemented following ACE (Agentic Context Engineering) principles from the research paper and handoff documentation.

## What Was Built

### 1. Core Components

#### **Bullet Schema** ([bullet.py](../core/memory/bullet.py))
- Modern dataclass with proper enums for type safety
- Fields include: id, text, side (hemisphere), type, tags, status, confidence, helpful/harmful counts, timestamps
- Built-in methods for scoring, promotion logic, and lifecycle management
- Supports serialization to/from dict and Chroma metadata format

**Key Classes:**
- `Bullet` - Main dataclass for procedural knowledge
- `BulletType` - Enum (TOOL_RULE, HEURISTIC, CHECKLIST, PITFALL, TEMPLATE, EXAMPLE, PATTERN, CONCEPT)
- `BulletStatus` - Enum (ACTIVE, QUARANTINED, DEPRECATED)
- `Hemisphere` - Enum (LEFT, RIGHT, SHARED)

#### **Procedural Memory Store** ([procedural_store.py](../core/memory/procedural_store.py))
- Low-level Chroma vector database interface
- Three separate collections: `procedural_left`, `procedural_right`, `procedural_shared`
- Embedding using Sentence Transformers
- CRUD operations with atomic bullet updates
- Automatic promotion to shared memory based on success thresholds
- Outcome-based scoring (NOT tick-based)

#### **ProceduralMemory Wrapper** ([procedural_memory.py](../core/memory/procedural_memory.py))
- High-level API for memory management
- Modern Bullet dataclass integration
- Simplified CRUD operations
- Automatic scoring and promotion logic
- Active bullet tracking per hemisphere
- Playbook formatting for LLM context

#### **MemoryRetriever** ([retrieval.py](../core/memory/retrieval.py))
- Advanced retrieval patterns:
  - Tool-specific retrieval
  - Error-handling retrieval
  - Multi-query fusion (rank-based and score-based)
  - Adaptive k selection
  - Type-based filtering
  - Recent and controversial bullet detection (stubs)

### 2. Integration with Agents

#### **Left Brain Agent** ([core/left_brain/agent.py](../core/left_brain/agent.py))
- Uses modern `ProceduralMemory` API
- Retrieves 8 bullets per query (pattern continuity focus)
- Higher confidence threshold (0.6)
- Formats bullets as structured playbook in prompts

#### **Right Brain Agent** ([core/right_brain/agent.py](../core/right_brain/agent.py))
- Uses modern `ProceduralMemory` API
- Retrieves 16 bullets per query (exploratory focus)
- Lower confidence threshold (0.4)
- More diverse retrieval for pattern violation

#### **BicameralMind Orchestrator** ([core/bicameral_mind.py](../core/bicameral_mind.py))
- Initializes shared `ProceduralMemory` instance
- Passes to both hemispheres
- Maintains separation between procedural memory and factual RAG

## Key Design Principles Implemented

### ✅ 1. **Bullet-Based Storage (NOT Summaries)**
- Each piece of knowledge is an atomic bullet
- Never rewrite entire playbooks
- Incremental addition and refinement

### ✅ 2. **Three Separate Collections**
```
procedural_left   → Left brain's knowledge
procedural_right  → Right brain's knowledge
procedural_shared → Consensus/promoted knowledge
```

### ✅ 3. **Outcome-Based Learning (NOT Tick-Based)**
**CRITICAL:** Helpful/harmful counters are ONLY incremented by:
- Tool success/failure
- Test pass/fail
- User confirmation/correction
- Validator results

**NOT by:**
- ❌ Consciousness ticks
- ❌ Time spent
- ❌ Iterations

### ✅ 4. **Automatic Promotion to Shared**
Bullets are promoted when:
- Status = ACTIVE
- helpful_count >= threshold (default: 3)
- harmful_count = 0
- Side = left or right (not already shared)

### ✅ 5. **Quarantine → Active Lifecycle**
New bullets start QUARANTINED and become ACTIVE after validation:
- helpful_count >= 2
- harmful_count = 0

### ✅ 6. **No Cross-Hemisphere Contamination**
- Each hemisphere maintains its own collection
- Shared memory is the ONLY way knowledge crosses over
- Prevents collapse into homogeneous thinking

### ✅ 7. **Comprehensive Playbooks (Not Concise)**
Following ACE principle: contexts should be **detailed playbooks**, not compressed summaries.
- LLMs benefit from long, detailed contexts
- They can distill relevance autonomously
- Better than human-style concise generalization

## File Structure

```
core/memory/
├── __init__.py                  # Exports: Bullet, ProceduralMemory, MemoryRetriever
├── bullet.py                    # Bullet dataclass + enums
├── procedural_store.py          # Low-level Chroma store (legacy compatible)
├── procedural_memory.py         # High-level API wrapper
└── retrieval.py                 # Advanced retrieval patterns

core/left_brain/
└── agent.py                     # ✅ Updated to use ProceduralMemory

core/right_brain/
└── agent.py                     # ✅ Updated to use ProceduralMemory

core/
└── bicameral_mind.py           # ✅ Updated to use ProceduralMemory

examples/
└── procedural_memory_example.py # Comprehensive usage examples
```

## Example Usage

### Adding Bullets

```python
from core.memory import ProceduralMemory, Bullet, BulletType, Hemisphere

memory = ProceduralMemory(config)

# Add to left brain
bullet = memory.add(
    text="Always validate API parameters before calling",
    side=Hemisphere.LEFT,
    bullet_type=BulletType.TOOL_RULE,
    tags=["api", "validation"],
    confidence=0.7,
)
```

### Retrieving Bullets

```python
# Retrieve for left brain
bullets, used_ids = memory.retrieve(
    query="How to handle API errors?",
    side=Hemisphere.LEFT,
    k=8,
    min_confidence=0.6,
)

# Format for prompt
playbook_str = memory.format_bullets_for_prompt(bullets)
```

### Recording Outcomes

```python
# Tool succeeded - mark as helpful
memory.record_outcome(used_ids, helpful=True, side=Hemisphere.LEFT)

# Tool failed - mark as harmful
memory.record_outcome(used_ids, helpful=False, side=Hemisphere.LEFT)
```

### Advanced Retrieval

```python
from core.memory import MemoryRetriever

retriever = MemoryRetriever(memory)

# Tool-specific retrieval
bullets, ids = retriever.retrieve_for_tool(
    tool_name="api",
    query="authentication",
    side=Hemisphere.LEFT,
)

# Multi-query fusion
bullets, ids = retriever.retrieve_multi_query(
    queries=["error handling", "API failures", "retry logic"],
    side=Hemisphere.LEFT,
    fusion_method="rank",
)
```

## Testing

Run the comprehensive example:

```bash
python examples/procedural_memory_example.py
```

This demonstrates:
1. Basic bullet CRUD operations
2. Retrieval from different hemispheres
3. Outcome-based learning and promotion
4. Advanced retrieval patterns

## Configuration

Add to `config/config.yaml`:

```yaml
procedural_memory:
  enabled: true
  persist_directory: "./data/memory/procedural"
  embedding_model: "sentence-transformers/all-MiniLM-L6-v2"

  # Learning policy
  cross_teaching: "shared_only"  # shared_only | suggestions
  promote_threshold: 3           # Helpful count for promotion
  quarantine_threshold: 2        # Harmful count for quarantine

  # Retrieval defaults
  k_left: 8                      # Bullets per left brain query
  k_right: 16                    # Bullets per right brain query
  k_shared: 5                    # Shared bullets per query
```

## Next Steps (Phase 2)

### Remaining TODOs:
1. **Deduplication Logic** - Identify and merge near-duplicate bullets
2. **Pruning Logic** - Remove persistently low-quality bullets
3. **Reflection Module** - Analyze execution traces to extract insights
4. **Curator Logic** - Automated bullet generation from reflections
5. **Tick Integration** - Connect consciousness ticks to reflection depth (NOT scoring)
6. **MCP Integration** - Tool outcome signals feed learning
7. **Episodic Trace Analytics** - Link bullets to execution traces

### Critical Reminders:
- ⚠️ **NEVER** increment helpful/harmful from ticks
- ⚠️ **ONLY** from actual outcomes (tool results, tests, user feedback)
- ⚠️ Ticks gate **reflection depth**, not learning signals
- ⚠️ Keep procedural memory **separate** from factual RAG

## References

- [ACE Paper](../docs/study.pdf) - Agentic Context Engineering research
- [Handoff Doc](../docs/Bicameral_Mind_Handoff.md) - Design philosophy
- [Checklist](../docs/Bicameral_Mind_Checklist.md) - Implementation checklist

---

**Status:** ✅ Phase 1 Complete - Procedural Memory Foundation Implemented

**Date:** December 24, 2025

**Next:** Reflection Module + Curator Logic (Phase 2)
