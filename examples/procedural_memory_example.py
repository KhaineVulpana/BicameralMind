"""Example usage of the Procedural Memory system.

This demonstrates:
1. Adding bullets to different hemispheres
2. Retrieving relevant bullets
3. Recording outcomes (helpful/harmful)
4. Automatic promotion to shared memory
5. Different retrieval patterns
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.memory import Bullet, BulletType, BulletStatus, Hemisphere, ProceduralMemory, MemoryRetriever
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def print_bullets(title: str, bullets: list[Bullet]):
    """Pretty print bullets."""
    if not bullets:
        console.print(f"[yellow]{title}: No bullets[/yellow]")
        return

    table = Table(title=title)
    table.add_column("ID", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Text", style="white")
    table.add_column("Score", style="green")
    table.add_column("Stats", style="blue")

    for bullet in bullets:
        table.add_row(
            bullet.id[:12],
            bullet.type.value,
            bullet.text[:60] + "..." if len(bullet.text) > 60 else bullet.text,
            f"{bullet.score():.2f}",
            f"+{bullet.helpful_count}/-{bullet.harmful_count}",
        )

    console.print(table)


def example_basic_usage():
    """Basic usage example."""
    console.print(Panel("[bold cyan]Example 1: Basic Usage[/bold cyan]"))

    # Initialize memory
    config = {
        "procedural_memory": {
            "enabled": True,
            "persist_directory": "./data/memory/procedural_example",
        }
    }
    memory = ProceduralMemory(config)

    console.print("\n[green]OK[/green] Initialized ProceduralMemory")

    # Add some bullets to left brain
    console.print("\n[bold]Adding bullets to LEFT brain...[/bold]")

    left_bullets = [
        ("Always validate API parameters before calling", BulletType.TOOL_RULE, ["api", "validation"]),
        ("Use try-except blocks for error handling", BulletType.HEURISTIC, ["error-handling"]),
        ("Check return codes before processing results", BulletType.CHECKLIST, ["api", "validation"]),
        ("API timeout errors often mean rate limiting", BulletType.PITFALL, ["api", "error"]),
    ]

    for text, btype, tags in left_bullets:
        bullet = memory.add(
            text=text,
            side=Hemisphere.LEFT,
            bullet_type=btype,
            tags=tags,
            confidence=0.7,
            status=BulletStatus.ACTIVE,  # Start active for demo
        )
        console.print(f"  OK Added: {bullet.id[:12]}... [{btype.value}]")

    # Add some bullets to right brain
    console.print("\n[bold]Adding bullets to RIGHT brain...[/bold]")

    right_bullets = [
        ("What if the API schema has changed?", BulletType.HEURISTIC, ["api", "debugging"]),
        ("Try alternative endpoints when primary fails", BulletType.HEURISTIC, ["api", "fallback"]),
        ("Consider rate limiting might be dynamic", BulletType.CONCEPT, ["api"]),
    ]

    for text, btype, tags in right_bullets:
        bullet = memory.add(
            text=text,
            side=Hemisphere.RIGHT,
            bullet_type=btype,
            tags=tags,
            confidence=0.6,
            status=BulletStatus.ACTIVE,
        )
        console.print(f"  OK Added: {bullet.id[:12]}... [{btype.value}]")

    # Retrieve bullets
    console.print("\n[bold]Retrieving bullets for query: 'How to handle API errors?'[/bold]")

    # Left brain retrieval
    left_results, left_ids = memory.retrieve(
        query="How to handle API errors?",
        side=Hemisphere.LEFT,
        k=3,
    )
    print_bullets("LEFT Brain Results", left_results)

    # Right brain retrieval
    right_results, right_ids = memory.retrieve(
        query="How to handle API errors?",
        side=Hemisphere.RIGHT,
        k=3,
    )
    print_bullets("RIGHT Brain Results", right_results)

    # Stats
    console.print("\n[bold]Memory Statistics:[/bold]")
    stats = memory.get_stats()
    for side, info in stats.get("collections", {}).items():
        console.print(f"  {side}: {info.get('count', 0)} bullets")


def example_outcome_based_learning():
    """Demonstrate outcome-based learning and promotion."""
    console.print(Panel("[bold cyan]Example 2: Outcome-Based Learning[/bold cyan]"))

    config = {
        "procedural_memory": {
            "enabled": True,
            "persist_directory": "./data/memory/procedural_example",
            "promote_threshold": 3,  # Promote after 3 successful uses
        }
    }
    memory = ProceduralMemory(config)

    # Add a bullet
    console.print("\n[bold]Adding a new bullet...[/bold]")
    bullet = memory.add(
        text="Always check authentication token before API calls",
        side=Hemisphere.LEFT,
        bullet_type=BulletType.TOOL_RULE,
        tags=["api", "auth"],
        confidence=0.5,
        status=BulletStatus.QUARANTINED,  # Start quarantined
    )
    console.print(f"  OK Added quarantined bullet: {bullet.id[:12]}...")
    console.print(f"    Status: {bullet.status.value}")
    console.print(f"    Score: {bullet.score():.2f}")

    # Simulate successful uses
    console.print("\n[bold]Simulating successful outcomes...[/bold]")
    for i in range(4):
        memory.record_outcome([bullet.id], helpful=True, side=Hemisphere.LEFT)
        console.print(f"  OK Recorded helpful outcome #{i+1}")

    # Retrieve again to see updated bullet
    console.print("\n[bold]Retrieving updated bullet...[/bold]")
    results, _ = memory.retrieve(
        query="authentication API",
        side=Hemisphere.LEFT,
        k=1,
    )

    if results:
        updated = results[0]
        console.print(f"  Updated Status: {updated.status.value}")
        console.print(f"  Score: {updated.score():.2f}")
        console.print(f"  Helpful/Harmful: +{updated.helpful_count}/-{updated.harmful_count}")
        console.print(f"  Should promote to shared: {updated.should_promote_to_shared(threshold=3)}")

    # Check shared memory
    console.print("\n[bold]Checking SHARED memory...[/bold]")
    shared_results, _ = memory.retrieve(
        query="authentication",
        side=Hemisphere.SHARED,
        k=5,
        include_shared=False,  # Only shared collection
    )
    print_bullets("SHARED Memory", shared_results)


def example_advanced_retrieval():
    """Demonstrate advanced retrieval patterns."""
    console.print(Panel("[bold cyan]Example 3: Advanced Retrieval[/bold cyan]"))

    config = {
        "procedural_memory": {
            "enabled": True,
            "persist_directory": "./data/memory/procedural_example",
        }
    }
    memory = ProceduralMemory(config)
    retriever = MemoryRetriever(memory)

    # Tool-specific retrieval
    console.print("\n[bold]Tool-specific retrieval for 'api'...[/bold]")
    tool_results, _ = retriever.retrieve_for_tool(
        tool_name="api",
        query="authentication",
        side=Hemisphere.LEFT,
        k=3,
    )
    print_bullets("Tool-Specific Results", tool_results)

    # Multi-query fusion
    console.print("\n[bold]Multi-query fusion...[/bold]")
    fusion_results, _ = retriever.retrieve_multi_query(
        queries=[
            "How to handle API errors?",
            "Error handling best practices",
            "API failure recovery",
        ],
        side=Hemisphere.LEFT,
        k=5,
        fusion_method="rank",
    )
    print_bullets("Fused Results", fusion_results)

    # Type-specific retrieval
    console.print("\n[bold]Retrieving only PITFALL and TOOL_RULE types...[/bold]")
    type_results, _ = retriever.retrieve_by_type(
        query="API usage",
        side=Hemisphere.LEFT,
        bullet_types=[BulletType.PITFALL, BulletType.TOOL_RULE],
        k=5,
    )
    print_bullets("Type-Filtered Results", type_results)


def main():
    """Run all examples."""
    console.print(Panel.fit(
        "[bold magenta]Procedural Memory System Examples[/bold magenta]\n"
        "Demonstrating ACE-inspired bullet-based learning",
        border_style="magenta"
    ))

    try:
        example_basic_usage()
        console.print("\n" + "=" * 80 + "\n")

        example_outcome_based_learning()
        console.print("\n" + "=" * 80 + "\n")

        example_advanced_retrieval()

    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        import traceback
        traceback.print_exc()

    console.print("\n[bold green]OK Examples completed![/bold green]")


if __name__ == "__main__":
    main()
