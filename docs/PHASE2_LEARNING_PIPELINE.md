# Phase 2: Learning Pipeline - Implementation Complete 

## Overview

**Phase 2** implements the complete learning cycle for the Bicameral Mind system, enabling automated extraction of insights from execution traces and their conversion into procedural bullets.

This builds on Phase 1's procedural memory foundation with the **Reflection -> Curation -> Learning** pipeline.

## What Was Built

### 1. Reflector Module ([reflector.py](../core/memory/reflector.py))

The Reflector analyzes execution traces to extract actionable insights.

**Key Features:**
- **Three reflection depths** (shallow, medium, deep)
- **Tick-gated reflection**: Tick rate controls depth, NOT scoring
- **Causal analysis**: Identifies what worked/failed and why
- **Insight extraction**: Generates structured insights with evidence

**Reflection Depths:**

| Tick Rate | Depth    | When Used                  | Analysis Level              |
|-----------|----------|----------------------------|-----------------------------|
| < 0.2     | none     | Very routine               | No reflection               |
| 0.2-0.5   | shallow  | Routine tasks              | Simple success/failure      |
| 0.5-0.8   | medium   | Mild novelty               | Pattern-based analysis      |
| > 0.8     | deep     | High novelty/failure       | LLM-powered causal analysis |

**Key Classes:**
- `ExecutionTrace` - Captures task execution details
- `ReflectionInsight` - Structured insight with evidence
- `Reflector` - Main reflection engine
- `InsightType` - Enum (STRATEGY, PITFALL, PATTERN, TOOL_RULE, HEURISTIC, EDGE_CASE)
- `OutcomeType` - Enum (SUCCESS, FAILURE, PARTIAL, UNCERTAIN)

### 2. Curator Module ([curator.py](../core/memory/curator.py))

The Curator converts insights into bullets and manages memory quality.

**Key Features:**
- **Insight -> Bullet conversion**: Transforms insights into actionable bullets
- **Duplicate detection**: Prevents redundant knowledge
- **Quality filtering**: Rejects low-confidence or trivial insights
- **Lifecycle management**: Quarantine -> Active -> Shared promotion
- **Maintenance operations**: Pruning and deduplication (implemented)

**Curation Flow:**
```
Insight (from Reflector)
    
Filter (confidence < 0.5, too short, etc.)
    
Convert to Bullet
    
Check Duplicates
    
Add to Memory (QUARANTINED status)
    
Outcome-based validation
    
ACTIVE status (helpful_count >= 2, harmful_count == 0)
    
PROMOTE TO SHARED (helpful_count >= 3, harmful_count == 0)
```

**Key Classes:**
- `Curator` - Main curation engine
- Methods: `curate()`, `prune_low_quality()`, `deduplicate()`, `promote_successful_bullets()`

### 3. Learning Pipeline ([learning_pipeline.py](../core/memory/learning_pipeline.py))

Orchestrates the complete learning cycle.

**Complete Learning Cycle:**

```
1. Execute Task
    
2. Generate ExecutionTrace
    
3. Check Tick Rate -> Determine Reflection Depth
    
4. Reflect (if tick rate sufficient)
    
5. Extract Insights
    
6. Curate Insights -> Create Bullets
    
7. Add Bullets to Memory (QUARANTINED)
    
8. Record Outcome for Bullets Used
    
9. Successful Bullets -> ACTIVE -> SHARED
```

**Key Features:**
- **Tick-gated reflection**: Consciousness ticks control reflection depth
- **Outcome recording**: Updates helpful/harmful counts
- **Learning history**: Tracks all learning cycles
- **Maintenance API**: Periodic pruning, deduplication, promotion
- **Statistics**: Comprehensive learning metrics

**Key Classes:**
- `LearningPipeline` - Main orchestrator
- `LearningResult` - Statistics from one learning cycle
- `create_trace()` - Helper function to build traces

## Critical Design Principles

###  1. **Ticks Gate Reflection Depth, NOT Scoring**

**CORRECT:**
```python
# Tick rate determines IF and HOW DEEPLY to reflect
should_reflect, depth = reflector.should_reflect(tick_rate, outcome)
if should_reflect:
    insights = await reflector.reflect(trace, depth=depth)
```

**INCORRECT:**
```python
#  NEVER use ticks to directly update scores
if tick_high:
    bullet.helpful_count += 1  # WRONG!
```

###  2. **Outcome-Based Scoring (NOT Tick-Based)**

**CORRECT:**
```python
# Only actual outcomes update scores
if task_succeeded:
    memory.record_outcome(bullet_ids, helpful=True)
else:
    memory.record_outcome(bullet_ids, helpful=False)
```

###  3. **Reflector Proposes, Curator Decides**

```
Reflector: "I found these insights..."
Curator: "I'll add these 3, skip these 2 duplicates"
Memory: "Added to quarantine, awaiting validation"
```

###  4. **Incremental Addition, Never Wholesale Rewrite**

ACE principle: Contexts grow incrementally, never rewritten wholesale.

```python
#  Add new bullet
curator.curate(insights, hemisphere, auto_add=True)

#  Rewrite entire playbook
# playbook = llm.summarize(old_playbook)  # WRONG!
```

## File Structure

```
core/memory/
 __init__.py                  #  Updated exports
 bullet.py                    # Bullet dataclass (Phase 1)
 procedural_store.py          # Low-level store (Phase 1)
 procedural_memory.py         # High-level API (Phase 1)
 retrieval.py                 # Advanced retrieval (Phase 1)
 reflector.py                 #  NEW (Phase 2)
 curator.py                   #  NEW (Phase 2)
 learning_pipeline.py         #  NEW (Phase 2)

examples/
 procedural_memory_example.py # Phase 1 examples
 learning_pipeline_example.py #  NEW (Phase 2)
```

## Example Usage

### Basic Learning Cycle

```python
from core.memory import (
    ProceduralMemory,
    LearningPipeline,
    create_trace,
)

# Initialize
memory = ProceduralMemory(config)
pipeline = LearningPipeline(memory, llm)

# After task execution, create trace
trace = create_trace(
    task="Call API to get weather data",
    hemisphere="left",
    steps=[
        {"description": "Validate API key", "success": True},
        {"description": "Make request", "success": True},
    ],
    bullets_used=["pb_left_123"],
    success=True,
    tools_called=["http_client"],
    tick_rate=0.5,  # Current tick rate
)

# Learn from trace
result = await pipeline.learn_from_trace(trace, tick_rate=0.5)

# Check results
print(f"Reflected: {result.reflected}")
print(f"Depth: {result.reflection_depth}")
print(f"Insights: {result.insights_extracted}")
print(f"Bullets created: {result.bullets_created}")
```

### Manual Outcome Recording

```python
# When you have explicit outcome signals
# (e.g., from MCP tool execution, user feedback)
pipeline.record_outcome(
    bullet_ids=["pb_left_123", "pb_left_456"],
    helpful=True,  # Tool succeeded
    hemisphere=Hemisphere.LEFT,
)
```

### Periodic Maintenance

```python
# Run nightly or weekly
stats = await pipeline.run_maintenance(
    hemisphere=Hemisphere.LEFT,
    prune=True,        # Remove low-quality bullets
    deduplicate=True,  # Merge duplicates
    promote=True,      # Check for promotable bullets
)
```

### Learning Statistics

```python
stats = pipeline.get_learning_stats()
print(f"Total learning cycles: {stats['total_cycles']}")
print(f"Average insights per cycle: {stats['avg_insights_per_cycle']:.2f}")
print(f"Total bullets created: {stats['total_bullets']}")
```

## Testing

Run the comprehensive example:

```bash
python examples/learning_pipeline_example.py
```

This demonstrates:
1. Basic learning cycle
2. Learning from failures
3. Tick-gated reflection
4. Learning statistics
5. Memory maintenance

## Integration with Agents

To integrate with left/right brain agents:

```python
class LeftBrain:
    async def process(self, message: Message) -> Message:
        # 1. Retrieve bullets
        bullets, used_ids = self.procedural_memory.retrieve(...)

        # 2. Execute task
        response = await self.execute_task(message, bullets)

        # 3. Create execution trace
        trace = create_trace(
            task=str(message.content),
            hemisphere="left",
            steps=execution_steps,
            bullets_used=used_ids,
            success=response.success,
            error_message=response.error if not response.success else None,
            tools_called=tools_used,
            tick_rate=self.meta_controller.get_tick_rate(),
        )

        # 4. Learn from execution
        learning_result = await self.learning_pipeline.learn_from_trace(
            trace,
            tick_rate=self.meta_controller.get_tick_rate(),
        )

        return response
```

## Next Steps (Future Enhancements)

### Remaining TODOs:
1. **MCP Integration** - Automatic outcome signals from tool execution
2. **Episodic Memory** - Link bullets to execution traces for replay
3. **Cross-hemisphere suggestions** - Optional teaching mode
4. **Multi-modal insights** - Extract from visual/audio traces

### Recommended Order:
1.  **Phase 1**: Procedural memory foundation -> DONE
2.  **Phase 2**: Reflection & curation pipeline -> DONE
3. **Phase 3**: MCP integration for automatic learning
4. **Phase 4**: Cross-hemisphere learning & suggestions
5. **Phase 5**: Additional modalities + policy hardening

## Configuration

Add to `config/config.yaml`:

```yaml
procedural_memory:
  enabled: true
  persist_directory: "./data/memory/procedural"

  # Phase 1 settings
  promote_threshold: 3
  quarantine_threshold: 2

  # Phase 2 settings
  learning:
    reflection_enabled: true
    auto_curate: true              # Automatically add curated bullets
    min_insight_confidence: 0.5    # Filter low-confidence insights
    deep_reflection_llm: true      # Use LLM for deep reflection

  maintenance:
    prune_enabled: false           # Not yet implemented
    deduplicate_enabled: false     # Not yet implemented
    prune_schedule: "daily"
    min_bullet_age_days: 7
    min_bullet_score: -0.5
```

## Key Takeaways

### What Phase 2 Adds:
-  **Automated learning** from execution traces
-  **Tick-gated reflection** (depth, not scoring)
-  **Insight extraction** with evidence
-  **Quality-controlled curation**
-  **Complete learning pipeline**

### Critical Reminders:
-  **Ticks gate DEPTH**, not scoring
-  **Outcomes update SCORES**, not ticks
-  **Reflector proposes**, Curator decides
-  **Add incrementally**, never rewrite
-  **Start QUARANTINED**, promote with validation

---

**Status:**  Phase 2 Complete - Learning Pipeline Implemented

**Date:** December 24, 2025

**Next:** MCP Integration for Automatic Tool Outcome Learning (Phase 3)
