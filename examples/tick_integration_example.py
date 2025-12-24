#!/usr/bin/env python3
"""Example: Automatic Tick Generation + Learning Pipeline Integration

This demonstrates how the meta_controller automatically calculates tick rates
from execution novelty, which then drives reflection depth in the learning pipeline.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.memory import (
    ProceduralMemory,
    LearningPipeline,
    create_trace,
)
from core.meta_controller import MetaController


class MockBrain:
    """Mock brain for meta_controller initialization."""
    def get_state_metrics(self):
        return {"entropy": 0.5, "confidence": 0.7}


async def example_automatic_tick_generation():
    """Demonstrate automatic tick generation from execution."""
    print("\n=== Example: Automatic Tick Generation ===\n")

    # Initialize components
    config = {
        "procedural_memory": {
            "enabled": True,
            "persist_directory": "./data/memory/tick_example",
        }
    }

    memory = ProceduralMemory(config)
    pipeline = LearningPipeline(memory)

    # Create meta_controller with mock brains
    left_brain = MockBrain()
    right_brain = MockBrain()
    meta_controller = MetaController({}, left_brain, right_brain)

    print("[OK] Initialized components\n")

    # Scenario 1: Routine Success (automatic low tick rate)
    print("Scenario 1: Routine Success")
    trace = create_trace(
        task="Call weather API",
        hemisphere="left",
        steps=[
            {"description": "Validate key", "success": True},
            {"description": "Make request", "success": True},
        ],
        bullets_used=[],
        success=True,
        confidence=0.9,
    )

    result = await pipeline.learn_from_trace_auto_tick(
        trace=trace,
        meta_controller=meta_controller,
        expected_success=True,
    )

    print(f"  Tick Rate (auto): {result.tick_rate:.2f}")
    print(f"  Reflected: {result.reflected}")
    print(f"  Depth: {result.reflection_depth}")
    print(f"  Insights: {result.insights_extracted}\n")

    # Scenario 2: Unexpected Failure (automatic high tick rate)
    print("Scenario 2: Unexpected Failure")
    trace = create_trace(
        task="Process payment",
        hemisphere="left",
        steps=[
            {"description": "Validate card", "success": True},
            {"description": "Call gateway", "success": False, "error": "Timeout"},
        ],
        bullets_used=[],
        success=False,
        error_message="Payment gateway timeout",
        confidence=0.6,
    )

    result = await pipeline.learn_from_trace_auto_tick(
        trace=trace,
        meta_controller=meta_controller,
        expected_success=True,  # Expected success, got failure → high novelty
    )

    print(f"  Tick Rate (auto): {result.tick_rate:.2f}")
    print(f"  Reflected: {result.reflected}")
    print(f"  Depth: {result.reflection_depth}")
    print(f"  Insights: {result.insights_extracted}\n")

    # Scenario 3: Low Confidence Task (automatic medium tick rate)
    print("Scenario 3: Low Confidence Task")
    trace = create_trace(
        task="Analyze complex data",
        hemisphere="right",
        steps=[
            {"description": "Parse data", "success": True},
            {"description": "Analyze patterns", "success": True},
        ],
        bullets_used=[],
        success=True,
        confidence=0.3,  # Low confidence despite success
    )

    result = await pipeline.learn_from_trace_auto_tick(
        trace=trace,
        meta_controller=meta_controller,
        expected_success=None,  # Uncertain what to expect
    )

    print(f"  Tick Rate (auto): {result.tick_rate:.2f}")
    print(f"  Reflected: {result.reflected}")
    print(f"  Depth: {result.reflection_depth}")
    print(f"  Insights: {result.insights_extracted}\n")

    print("[OK] Automatic tick generation demonstration complete!\n")


async def example_manual_vs_automatic():
    """Compare manual vs automatic tick rate specification."""
    print("\n=== Example: Manual vs Automatic Ticks ===\n")

    config = {
        "procedural_memory": {
            "enabled": True,
            "persist_directory": "./data/memory/tick_example",
        }
    }

    memory = ProceduralMemory(config)
    pipeline = LearningPipeline(memory)
    meta_controller = MetaController({}, MockBrain(), MockBrain())

    # Same trace, different methods
    trace = create_trace(
        task="Complex analysis",
        hemisphere="left",
        steps=[{"description": "Analyze", "success": True}],
        bullets_used=[],
        success=True,
        confidence=0.4,
    )

    # Manual tick specification
    print("Manual Tick Specification:")
    result1 = await pipeline.learn_from_trace(trace, tick_rate=0.7)
    print(f"  Tick Rate (manual): {result1.tick_rate:.2f}")
    print(f"  Reflection Depth: {result1.reflection_depth}\n")

    # Automatic tick calculation
    print("Automatic Tick Calculation:")
    result2 = await pipeline.learn_from_trace_auto_tick(
        trace=trace,
        meta_controller=meta_controller,
    )
    print(f"  Tick Rate (auto): {result2.tick_rate:.2f}")
    print(f"  Reflection Depth: {result2.reflection_depth}\n")

    print("[OK] Comparison complete!\n")


async def example_novelty_accumulation():
    """Show how novelty accumulates over multiple executions."""
    print("\n=== Example: Novelty Accumulation ===\n")

    config = {
        "procedural_memory": {
            "enabled": True,
            "persist_directory": "./data/memory/tick_example",
        }
    }

    memory = ProceduralMemory(config)
    pipeline = LearningPipeline(memory)
    meta_controller = MetaController({}, MockBrain(), MockBrain())

    print("Simulating sequence of tasks:\n")

    tasks = [
        ("Routine 1", True, 0.9),
        ("Routine 2", True, 0.85),
        ("FAILURE!", False, 0.5),  # Spike in novelty
        ("Routine 3", True, 0.9),
        ("Routine 4", True, 0.95),
    ]

    for task_name, success, confidence in tasks:
        trace = create_trace(
            task=task_name,
            hemisphere="left",
            steps=[{"description": "Do something", "success": success}],
            bullets_used=[],
            success=success,
            error_message="Error" if not success else None,
            confidence=confidence,
        )

        result = await pipeline.learn_from_trace_auto_tick(
            trace=trace,
            meta_controller=meta_controller,
            expected_success=True,
        )

        novelty = meta_controller.get_current_novelty()

        print(f"  {task_name:12} | Tick: {result.tick_rate:.2f} | "
              f"Current Novelty: {novelty:.2f} | Depth: {result.reflection_depth}")

    print("\n[OK] Novelty accumulation demonstration complete!\n")


async def main():
    """Run all examples."""
    print("\n" + "=" * 75)
    print("Automatic Tick Generation Examples - Phase 2.5")
    print("=" * 75)

    try:
        await example_automatic_tick_generation()
        print("=" * 75 + "\n")

        await example_manual_vs_automatic()
        print("=" * 75 + "\n")

        await example_novelty_accumulation()

        print("=" * 75)
        print("[OK] All examples completed successfully!")
        print("=" * 75 + "\n")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
