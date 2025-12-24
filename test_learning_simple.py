#!/usr/bin/env python3
"""Simple test to verify Phase 2 learning pipeline works."""

import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.memory import (
    ProceduralMemory,
    LearningPipeline,
    create_trace,
    Hemisphere,
)

async def test_basic_learning():
    """Test basic learning cycle."""
    print("\n=== Testing Basic Learning Cycle ===\n")

    # Initialize
    config = {
        "procedural_memory": {
            "enabled": True,
            "persist_directory": "./data/memory/test_learning",
        }
    }
    memory = ProceduralMemory(config)
    pipeline = LearningPipeline(memory)

    print("[OK] Initialized learning pipeline")

    # Create a successful task trace
    trace = create_trace(
        task="Call weather API to get current temperature",
        hemisphere="left",
        steps=[
            {"description": "Validate API key", "success": True},
            {"description": "Make HTTP request", "success": True},
            {"description": "Parse JSON response", "success": True},
        ],
        bullets_used=["pb_left_123"],
        success=True,
        tools_called=["http_client", "json_parser"],
        tick_rate=0.3,  # Low tick rate (routine task)
        confidence=0.8,
    )

    print("[OK] Created execution trace")

    # Learn from trace
    result = await pipeline.learn_from_trace(trace, tick_rate=0.3)

    # Display results
    print(f"\nLearning Result:")
    print(f"  Reflected: {result.reflected}")
    print(f"  Depth: {result.reflection_depth}")
    print(f"  Insights extracted: {result.insights_extracted}")
    print(f"  Bullets created: {result.bullets_created}")
    print(f"  Bullets marked helpful: {result.bullets_marked_helpful}")

    print("\n[OK] Basic learning cycle complete!\n")
    return True


async def test_failure_learning():
    """Test learning from failures."""
    print("\n=== Testing Failure Learning ===\n")

    config = {
        "procedural_memory": {
            "enabled": True,
            "persist_directory": "./data/memory/test_learning",
        }
    }
    memory = ProceduralMemory(config)
    pipeline = LearningPipeline(memory)

    # Create a failure trace
    trace = create_trace(
        task="Call payment API to process transaction",
        hemisphere="left",
        steps=[
            {"description": "Validate card number", "success": True},
            {"description": "Call payment gateway", "success": False, "error": "Timeout"},
            {"description": "Retry with backoff", "success": False, "error": "Connection refused"},
        ],
        bullets_used=["pb_left_789"],
        success=False,
        error_message="Payment gateway connection failed after retries",
        tools_called=["payment_api", "retry_helper"],
        tick_rate=0.9,  # High tick rate (failure!)
        confidence=0.4,
    )

    print("[OK] Created failure trace")

    # Learn from failure
    result = await pipeline.learn_from_trace(trace, tick_rate=0.9)

    print(f"\nLearning Result:")
    print(f"  Reflected: {result.reflected}")
    print(f"  Depth: {result.reflection_depth} (deep due to failure)")
    print(f"  Insights extracted: {result.insights_extracted}")
    print(f"  Bullets created: {result.bullets_created}")
    print(f"  Bullets marked harmful: {result.bullets_marked_harmful}")

    print("\n[OK] Failure learning complete!\n")
    return True


async def test_tick_gated_reflection():
    """Test tick-gated reflection depths."""
    print("\n=== Testing Tick-Gated Reflection ===\n")

    config = {
        "procedural_memory": {
            "enabled": True,
            "persist_directory": "./data/memory/test_learning",
        }
    }
    memory = ProceduralMemory(config)
    pipeline = LearningPipeline(memory)

    # Test different tick rates
    scenarios = [
        ("Routine task", 0.1, "none or shallow"),
        ("Mild novelty", 0.5, "medium"),
        ("High novelty", 0.85, "deep"),
        ("Failure", 0.95, "deep"),
    ]

    print("Scenario                Tick Rate    Expected Depth    Actual Depth")
    print("-" * 75)

    for scenario_name, tick_rate, expected_depth in scenarios:
        trace = create_trace(
            task=f"Test task: {scenario_name}",
            hemisphere="left",
            steps=[{"description": "Do something", "success": True}],
            bullets_used=[],
            success=(tick_rate < 0.9),
            error_message="Failed" if tick_rate >= 0.9 else None,
            tick_rate=tick_rate,
        )

        result = await pipeline.learn_from_trace(trace, tick_rate=tick_rate)

        actual_depth = result.reflection_depth if result.reflected else "none"
        print(f"{scenario_name:24} {tick_rate:6.2f}       {expected_depth:16}  {actual_depth:12}")

    print("\nNote: Ticks gate reflection DEPTH, not outcome scoring!")
    print("[OK] Tick-gated reflection test complete!\n")
    return True


async def main():
    """Run all tests."""
    print("\n" + "=" * 75)
    print("Learning Pipeline Tests - Phase 2")
    print("=" * 75)

    try:
        await test_basic_learning()
        await test_failure_learning()
        await test_tick_gated_reflection()

        print("=" * 75)
        print("[OK] All tests completed successfully!")
        print("=" * 75 + "\n")
        return 0

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
