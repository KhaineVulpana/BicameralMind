# Phase 2.5: Automatic Tick Generation - Implementation Complete ✅

Last Updated: December 24, 2025

## Overview

**Phase 2.5** implements automatic consciousness tick generation based on execution novelty. This completes the missing piece between Phase 2 (Learning Pipeline) and provides true adaptive learning.

**Key Insight**: Ticks are no longer manually specified - they're automatically calculated from surprise/novelty in execution.

## What Was Built

### 1. Novelty Detector ([novelty_detector.py](../core/meta_controller/novelty_detector.py))

Detects novelty/surprise in task execution to generate consciousness ticks.

**Novelty Sources**:
1. **Prediction Errors** - Expected outcome != Actual outcome
2. **Execution Failures** - Task failed unexpectedly
3. **Low Confidence** - Agent is uncertain
4. **Tool Failures** - Individual tools failed
5. **Unexpected Success** - Succeeded despite low confidence

**Key Classes**:
- `NoveltyDetector` - Main novelty measurement engine
- `NoveltySignal` - Enum of novelty signal types
- `NoveltyMeasurement` - Single novelty measurement with evidence

**Tick Rate Mapping**:
```
Tick Rate       Reflection Depth    When Used
---------------------------------------------------------------------------
0.0 - 0.2       none/shallow        Routine, expected success
0.2 - 0.5       shallow             Minor surprises
0.5 - 0.8       medium              Moderate novelty, low confidence
0.8 - 1.0       deep                Failures, high surprise, major novelty
```

**Key Methods**:
```python
detector = NoveltyDetector()

# Measure novelty from execution details
tick_rate = detector.measure_novelty(
    expected_outcome=True,
    actual_outcome=False,  # Surprise!
    confidence=0.5,
    tools_used=["api_call"],
    tool_results={"api_call": False},
    error_message="Connection timeout",
)
# Returns: tick_rate = 1.0 (high novelty → deep reflection)

# Measure from execution trace
tick_rate = detector.measure_from_trace(trace_data, expected_success=True)
```

### 2. Meta Controller Enhancement ([controller.py](../core/meta_controller/controller.py))

Enhanced to integrate novelty detection.

**New Methods**:
```python
meta_controller = MetaController(config, left_brain, right_brain)

# Calculate tick rate from execution
tick_rate = meta_controller.calculate_novelty_tick_rate(
    expected_outcome=True,
    actual_outcome=False,
    confidence=0.6,
    tools_used=["payment_api"],
    tool_results={"payment_api": False},
    error_message="Timeout",
)

# Calculate from trace dict
tick_rate = meta_controller.calculate_tick_rate_from_trace(
    trace_data={
        "success": False,
        "confidence": 0.5,
        "tools_called": ["api"],
        "error_message": "Failed",
        ...
    },
    expected_success=True,
)

# Get current novelty level (moving average)
current_novelty = meta_controller.get_current_novelty()

# Get detailed stats
stats = meta_controller.get_novelty_stats()
```

### 3. Learning Pipeline Integration ([learning_pipeline.py](../core/memory/learning_pipeline.py))

New method for automatic tick calculation.

**New API**:
```python
pipeline = LearningPipeline(memory, llm)
meta_controller = MetaController(config, left_brain, right_brain)

# OLD: Manual tick specification
result = await pipeline.learn_from_trace(trace, tick_rate=0.7)

# NEW: Automatic tick calculation
result = await pipeline.learn_from_trace_auto_tick(
    trace=trace,
    meta_controller=meta_controller,
    expected_success=True,  # Optional for novelty comparison
)
```

## How It Works

### Complete Learning Cycle with Automatic Ticks

```
1. Execute Task
    ↓
2. Generate ExecutionTrace
    ↓
3. Calculate Novelty (meta_controller)
    - Compare expected vs actual
    - Measure confidence gap
    - Detect tool failures
    - Detect execution errors
    ↓
4. Generate Tick Rate (0.0 - 1.0)
    - Low novelty → Low tick rate
    - High novelty → High tick rate
    ↓
5. Tick-Gated Reflection (reflector)
    - tick < 0.2 → No reflection
    - 0.2-0.5 → Shallow reflection
    - 0.5-0.8 → Medium reflection
    - 0.8-1.0 → Deep reflection
    ↓
6. Extract Insights (if reflected)
    ↓
7. Curate to Bullets
    ↓
8. Add to Memory (QUARANTINED)
    ↓
9. Record Outcomes
    ↓
10. Activate & Promote
```

### Novelty Calculation Algorithm

```python
def calculate_tick_rate(measurements):
    if no_novelty_signals:
        return 0.1  # Routine task

    # Average novelty magnitude from all signals
    avg_magnitude = sum(m.magnitude for m in measurements) / len(measurements)

    # Boost for multiple concurrent signals
    signal_boost = min(len(measurements) * 0.1, 0.3)

    # Final tick rate
    tick_rate = min(avg_magnitude + signal_boost, 1.0)
    return tick_rate
```

### Moving Average (Novelty Accumulation)

Novelty doesn't reset immediately - it accumulates and decays:

```python
# Exponential moving average
current_novelty = (
    decay_factor * previous_novelty +
    (1 - decay_factor) * new_tick_rate
)

# Default decay_factor = 0.8
# This means:
# - After high novelty, system stays alert for a while
# - Multiple routine tasks gradually reduce novelty
# - Recent failures influence current state
```

## Testing

### Run Tick Generation Tests
```bash
python test_tick_generation.py
```

Tests include:
- Basic novelty detection
- Novelty from traces
- Tick rate mapping
- Moving average accumulation
- Statistics tracking

### Run Integration Examples
```bash
python examples/tick_integration_example.py
```

Examples demonstrate:
- Automatic tick generation
- Manual vs automatic comparison
- Novelty accumulation over time

## Example Usage

### Basic: Automatic Tick Generation

```python
from core.memory import ProceduralMemory, LearningPipeline, create_trace
from core.meta_controller import MetaController

# Initialize
memory = ProceduralMemory(config)
pipeline = LearningPipeline(memory)
meta_controller = MetaController(config, left_brain, right_brain)

# Execute task and create trace
trace = create_trace(
    task="Call payment API",
    hemisphere="left",
    steps=[
        {"description": "Validate", "success": True},
        {"description": "Process", "success": False, "error": "Timeout"},
    ],
    bullets_used=["pb_left_123"],
    success=False,
    error_message="Payment gateway timeout",
    confidence=0.6,
)

# Learn with automatic tick calculation
result = await pipeline.learn_from_trace_auto_tick(
    trace=trace,
    meta_controller=meta_controller,
    expected_success=True,  # Expected success, got failure → high novelty
)

print(f"Tick Rate (auto): {result.tick_rate:.2f}")  # ~0.9-1.0
print(f"Reflection Depth: {result.reflection_depth}")  # "deep"
print(f"Insights Extracted: {result.insights_extracted}")  # 3-4
```

### Advanced: Direct Novelty Measurement

```python
from core.meta_controller import NoveltyDetector

detector = NoveltyDetector()

# Scenario 1: Routine success
tick1 = detector.measure_novelty(
    expected_outcome=True,
    actual_outcome=True,
    confidence=0.9,
)
# tick1 ≈ 0.1 (very routine)

# Scenario 2: Unexpected failure
tick2 = detector.measure_novelty(
    expected_outcome=True,
    actual_outcome=False,
    confidence=0.7,
    error_message="Connection timeout",
    tools_used=["api"],
    tool_results={"api": False},
)
# tick2 ≈ 1.0 (high novelty)

# Get current novelty level (moving average)
current = detector.get_current_tick_rate()

# Get detailed statistics
stats = detector.get_stats()
```

### Integration with Agents

```python
class LeftBrain:
    def __init__(self, config, llm, meta_controller, procedural_memory):
        self.meta_controller = meta_controller
        self.procedural_memory = procedural_memory
        self.learning_pipeline = LearningPipeline(procedural_memory, llm)

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
            confidence=response.confidence,
        )

        # 4. Learn with automatic tick calculation
        learning_result = await self.learning_pipeline.learn_from_trace_auto_tick(
            trace=trace,
            meta_controller=self.meta_controller,
            expected_success=True,  # Or predict based on confidence
        )

        return response
```

## Configuration

Add to `config/config.yaml`:

```yaml
novelty_detection:
  novelty_decay: 0.8  # Exponential moving average decay (0.0-1.0)

procedural_memory:
  learning:
    reflection_enabled: true
    auto_curate: true
    min_insight_confidence: 0.5
```

## Key Design Principles

### ✅ 1. Novelty Generates Ticks, NOT Manual Specification

**BEFORE (Phase 2)**:
```python
# Manual tick specification
trace = create_trace(task="...", tick_rate=0.7)  # How do you know?
result = await pipeline.learn_from_trace(trace, tick_rate=0.7)
```

**AFTER (Phase 2.5)**:
```python
# Automatic tick generation
trace = create_trace(task="...")  # No tick_rate needed
result = await pipeline.learn_from_trace_auto_tick(trace, meta_controller)
# System calculates tick_rate from execution novelty
```

### ✅ 2. Ticks Control Reflection Depth, NOT Scoring

This principle remains unchanged from Phase 2:
- High ticks → Deep reflection → More insights extracted
- Low ticks → No/shallow reflection → Efficient execution
- Outcomes (success/failure) update bullet scores, NOT ticks

### ✅ 3. Novelty Signals Are Evidence-Based

Every novelty measurement includes:
- Signal type (prediction_error, tool_failure, etc.)
- Magnitude (0.0-1.0)
- Evidence (what was surprising)
- Context (execution details)

### ✅ 4. Moving Average Prevents Oscillation

Novelty doesn't spike and drop instantly:
- High novelty event → System stays alert
- Multiple routine tasks → Gradual return to baseline
- Prevents thrashing between reflection modes

## Testing Results

All tests passing:

```
=== Tick Generation Tests ===
✓ Basic Novelty Detection
✓ Novelty from Trace
✓ Tick Rate Mapping
✓ Moving Average
✓ Novelty Statistics

=== Integration Examples ===
✓ Automatic Tick Generation
✓ Manual vs Automatic Comparison
✓ Novelty Accumulation
```

## Next Steps (Phase 3)

With automatic tick generation complete, the next logical step is:

**Phase 3: MCP Integration for Automatic Tool Outcome Learning**

Now that we have:
- ✅ Procedural memory (Phase 1)
- ✅ Learning pipeline (Phase 2)
- ✅ Automatic tick generation (Phase 2.5)

We can integrate with MCP to:
- Automatically capture tool executions
- Generate traces from tool calls
- Calculate novelty from tool outcomes
- Learn from real production tool usage

## Files Created/Modified

**Created**:
- `core/meta_controller/novelty_detector.py` - Novelty detection engine
- `test_tick_generation.py` - Test suite for tick generation
- `examples/tick_integration_example.py` - Integration examples

**Modified**:
- `core/meta_controller/controller.py` - Added novelty integration
- `core/meta_controller/__init__.py` - Exported novelty components
- `core/memory/learning_pipeline.py` - Added `learn_from_trace_auto_tick()`

**Documentation**:
- `docs/PHASE2_5_TICK_GENERATION.md` - This document

## Critical Reminders

- ⚠️ **Novelty generates ticks**, not manual specification
- ⚠️ **Ticks control DEPTH**, not scoring
- ⚠️ **Outcomes update SCORES**, not ticks
- ⚠️ **Moving average prevents oscillation**
- ⚠️ **Evidence-based measurements** for transparency

---

**Status**: ✅ Phase 2.5 Complete - Automatic Tick Generation Implemented

**Date**: December 24, 2025

**Next**: Phase 3 - MCP Integration for Automatic Tool Learning
