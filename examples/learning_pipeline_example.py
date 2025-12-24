#!/usr/bin/env python3
"""Learning Pipeline Example - Phase 2 Features.

This demonstrates the complete learning cycle:
1. Execute task → Generate trace
2. Reflect on trace (depth based on tick rate)
3. Extract insights
4. Curate into bullets
5. Record outcomes
6. Promote successful bullets
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
    Hemisphere,
    OutcomeType,
)
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


async def example_basic_learning_cycle():
    """Demonstrate basic learning cycle."""
    console.print("\n[bold cyan]Example 1: Basic Learning Cycle[/bold cyan]\n")

    # Initialize
    config = {
        "procedural_memory": {
            "enabled": True,
            "persist_directory": "./data/memory/learning_example",
        }
    }
    memory = ProceduralMemory(config)
    pipeline = LearningPipeline(memory)

    console.print("[green]✓[/green] Initialized learning pipeline")

    # Simulate a successful task execution
    console.print("\n[bold]Scenario: Successful API call[/bold]")

    trace = create_trace(
        task="Call weather API to get current temperature",
        hemisphere="left",
        steps=[
            {"description": "Validate API key", "success": True},
            {"description": "Make HTTP request", "success": True},
            {"description": "Parse JSON response", "success": True},
        ],
        bullets_used=["pb_left_123", "pb_left_456"],  # Hypothetical bullets
        success=True,
        tools_called=["http_client", "json_parser"],
        tick_rate=0.3,  # Low tick rate (routine task)
        confidence=0.8,
    )

    # Learn from trace
    result = await pipeline.learn_from_trace(trace, tick_rate=0.3)

    # Display results
    console.print(f"\n[bold]Learning Result:[/bold]")
    console.print(f"  Reflected: {result.reflected}")
    console.print(f"  Depth: {result.reflection_depth}")
    console.print(f"  Insights extracted: {result.insights_extracted}")
    console.print(f"  Bullets created: {result.bullets_created}")
    console.print(f"  Bullets marked helpful: {result.bullets_marked_helpful}")

    console.print("[green]✓ Basic learning cycle complete![/green]\n")


async def example_failure_learning():
    """Demonstrate learning from failures."""
    console.print("[bold cyan]Example 2: Learning from Failures[/bold cyan]\n")

    config = {
        "procedural_memory": {
            "enabled": True,
            "persist_directory": "./data/memory/learning_example",
        }
    }
    memory = ProceduralMemory(config)
    pipeline = LearningPipeline(memory)

    console.print("[bold]Scenario: Failed API call[/bold]")

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

    # Learn from failure
    result = await pipeline.learn_from_trace(trace, tick_rate=0.9)

    console.print(f"\n[bold]Learning Result:[/bold]")
    console.print(f"  Reflected: {result.reflected}")
    console.print(f"  Depth: {result.reflection_depth} [red](deep due to failure)[/red]")
    console.print(f"  Insights extracted: {result.insights_extracted}")
    console.print(f"  Bullets created: {result.bullets_created}")
    console.print(f"  Bullets marked harmful: {result.bullets_marked_harmful}")

    console.print("[green]✓ Failure learning complete![/green]\n")


async def example_tick_gated_reflection():
    """Demonstrate how tick rate gates reflection depth."""
    console.print("[bold cyan]Example 3: Tick-Gated Reflection[/bold cyan]\n")

    config = {
        "procedural_memory": {
            "enabled": True,
            "persist_directory": "./data/memory/learning_example",
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

    table = Table(title="Tick Rate → Reflection Depth")
    table.add_column("Scenario", style="cyan")
    table.add_column("Tick Rate", style="magenta")
    table.add_column("Expected Depth", style="yellow")
    table.add_column("Actual Depth", style="green")

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

        table.add_row(
            scenario_name,
            f"{tick_rate:.2f}",
            expected_depth,
            result.reflection_depth if result.reflected else "none",
        )

    console.print(table)
    console.print("\n[dim]Note: Ticks gate reflection DEPTH, not outcome scoring![/dim]")
    console.print("[green]✓ Tick-gated reflection demonstration complete![/green]\n")


async def example_learning_stats():
    """Show learning statistics."""
    console.print("[bold cyan]Example 4: Learning Statistics[/bold cyan]\n")

    config = {
        "procedural_memory": {
            "enabled": True,
            "persist_directory": "./data/memory/learning_example",
        }
    }
    memory = ProceduralMemory(config)
    pipeline = LearningPipeline(memory)

    # Simulate multiple learning cycles
    console.print("[bold]Simulating 10 learning cycles...[/bold]")

    for i in range(10):
        trace = create_trace(
            task=f"Task {i+1}",
            hemisphere="left" if i % 2 == 0 else "right",
            steps=[{"description": f"Step {j}", "success": True} for j in range(3)],
            bullets_used=[f"pb_{i}"],
            success=(i % 3 != 0),  # 2/3 success rate
            tick_rate=0.3 + (i * 0.05),  # Increasing complexity
        )

        await pipeline.learn_from_trace(trace, tick_rate=trace.tick_rate)

    # Get stats
    stats = pipeline.get_learning_stats()

    console.print(f"\n[bold]Learning Statistics:[/bold]")
    for key, value in stats.items():
        console.print(f"  {key}: {value}")

    console.print("[green]✓ Learning statistics complete![/green]\n")


async def example_maintenance():
    """Demonstrate memory maintenance."""
    console.print("[bold cyan]Example 5: Memory Maintenance[/bold cyan]\n")

    config = {
        "procedural_memory": {
            "enabled": True,
            "persist_directory": "./data/memory/learning_example",
        }
    }
    memory = ProceduralMemory(config)
    pipeline = LearningPipeline(memory)

    console.print("[bold]Running maintenance tasks...[/bold]")

    # Run maintenance
    maintenance_stats = await pipeline.run_maintenance(
        hemisphere=Hemisphere.LEFT,
        prune=True,
        deduplicate=True,
        promote=True,
    )

    console.print(f"\n[bold]Maintenance Results:[/bold]")
    for key, value in maintenance_stats.items():
        console.print(f"  {key}: {value}")

    console.print("\n[dim]Note: Pruning and deduplication are stubs in current implementation[/dim]")
    console.print("[green]✓ Maintenance demonstration complete![/green]\n")


async def main():
    """Run all examples."""
    console.print(Panel.fit(
        "[bold magenta]Learning Pipeline Examples - Phase 2[/bold magenta]\n"
        "Complete reflection → curation → learning cycle",
        border_style="magenta"
    ))

    try:
        await example_basic_learning_cycle()
        console.print("=" * 80 + "\n")

        await example_failure_learning()
        console.print("=" * 80 + "\n")

        await example_tick_gated_reflection()
        console.print("=" * 80 + "\n")

        await example_learning_stats()
        console.print("=" * 80 + "\n")

        await example_maintenance()

    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        import traceback
        traceback.print_exc()

    console.print("[bold green]✓ All examples completed![/bold green]\n")


if __name__ == "__main__":
    asyncio.run(main())
