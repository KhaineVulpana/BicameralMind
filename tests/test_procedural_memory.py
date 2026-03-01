#!/usr/bin/env python3
"""Quick test to verify procedural memory implementation."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.memory import Bullet, BulletType, BulletStatus, Hemisphere, ProceduralMemory
from rich.console import Console

console = Console()


def test_basic_operations():
    """Test basic CRUD operations."""
    console.print("\n[bold cyan]Test 1: Basic Operations[/bold cyan]")

    config = {
        "procedural_memory": {
            "enabled": True,
            "persist_directory": "./data/memory/test_procedural",
        }
    }

    memory = ProceduralMemory(config)
    console.print("  OK ProceduralMemory initialized")

    # Add a bullet
    bullet = memory.add(
        text="Test bullet: Always check inputs",
        side=Hemisphere.LEFT,
        bullet_type=BulletType.HEURISTIC,
        tags=["test"],
        status=BulletStatus.ACTIVE,
    )
    console.print(f"  OK Added bullet: {bullet.id[:16]}...")

    # Retrieve
    results, ids = memory.retrieve(
        query="input validation",
        side=Hemisphere.LEFT,
        k=5,
    )
    console.print(f"  OK Retrieved {len(results)} bullets")
    assert results, "Expected at least one bullet to be retrieved"

    # Record outcome
    if ids:
        memory.record_outcome(ids[:1], helpful=True, side=Hemisphere.LEFT)
        console.print("  OK Recorded helpful outcome")

    console.print("[green]OK Basic operations test passed![/green]\n")


def test_bullet_dataclass():
    """Test Bullet dataclass."""
    console.print("[bold cyan]Test 2: Bullet Dataclass[/bold cyan]")

    # Create bullet
    bullet = Bullet.create(
        text="Test heuristic",
        side=Hemisphere.RIGHT,
        bullet_type=BulletType.HEURISTIC,
        tags=["test", "validation"],
    )
    console.print(f"  OK Created bullet: {bullet.id[:16]}...")
    assert bullet.id, "Bullet id should not be empty"

    # Test scoring
    score = bullet.score()
    console.print(f"  OK Initial score: {score:.2f}")

    # Test marking
    bullet.mark_helpful()
    bullet.mark_helpful()
    console.print(f"  OK Marked helpful: +{bullet.helpful_count}")

    new_score = bullet.score()
    console.print(f"  OK New score: {new_score:.2f}")
    assert new_score > score, "Score should increase after helpful marks"

    # Test should_promote
    should_promote = bullet.should_promote_to_shared(threshold=2)
    console.print(f"  OK Should promote: {should_promote}")

    # Test serialization
    data = bullet.to_dict()
    restored = Bullet.from_dict(data)
    console.print("  OK Serialization works")
    assert restored.text == bullet.text

    console.print("[green]OK Bullet dataclass test passed![/green]\n")


def test_hemisphere_separation():
    """Test that hemispheres maintain separate collections."""
    console.print("[bold cyan]Test 3: Hemisphere Separation[/bold cyan]")

    config = {
        "procedural_memory": {
            "enabled": True,
            "persist_directory": "./data/memory/test_procedural",
        }
    }

    memory = ProceduralMemory(config)

    # Add to left
    left_bullet = memory.add(
        text="Left brain bullet",
        side=Hemisphere.LEFT,
        bullet_type=BulletType.TOOL_RULE,
        tags=["left"],
        status=BulletStatus.ACTIVE,
    )
    console.print("  OK Added bullet to LEFT")

    # Add to right
    right_bullet = memory.add(
        text="Right brain bullet",
        side=Hemisphere.RIGHT,
        bullet_type=BulletType.HEURISTIC,
        tags=["right"],
        status=BulletStatus.ACTIVE,
    )
    console.print("  OK Added bullet to RIGHT")

    # Query left (should not get right's bullet without shared)
    left_results, _ = memory.retrieve(
        query="bullet",
        side=Hemisphere.LEFT,
        k=10,
        include_shared=False,  # Don't include shared
    )

    right_results, _ = memory.retrieve(
        query="bullet",
        side=Hemisphere.RIGHT,
        k=10,
        include_shared=False,
    )

    console.print(f"  OK Left retrieved: {len(left_results)} bullets")
    console.print(f"  OK Right retrieved: {len(right_results)} bullets")

    left_ids = {b.id for b in left_results}
    right_ids = {b.id for b in right_results}
    assert left_bullet.id in left_ids
    assert right_bullet.id in right_ids
    assert right_bullet.id not in left_ids
    assert left_bullet.id not in right_ids

    # Get stats
    stats = memory.get_stats()
    console.print(f"  OK Stats: {stats}")

    console.print("[green]OK Hemisphere separation test passed![/green]\n")


def _run_test(test_fn):
    try:
        test_fn()
        return True
    except Exception as e:
        console.print(f"[red]X {test_fn.__name__} failed: {e}[/red]\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    console.print("\n" + "=" * 60)
    console.print("[bold magenta]Procedural Memory System Test Suite[/bold magenta]")
    console.print("=" * 60 + "\n")

    results = []

    # Run tests
    results.append(("Basic Operations", _run_test(test_basic_operations)))
    results.append(("Bullet Dataclass", _run_test(test_bullet_dataclass)))
    results.append(("Hemisphere Separation", _run_test(test_hemisphere_separation)))

    # Summary
    console.print("=" * 60)
    console.print("[bold]Test Summary:[/bold]")
    for test_name, passed in results:
        status = "[green]OK PASS[/green]" if passed else "[red]X FAIL[/red]"
        console.print(f"  {status} - {test_name}")

    all_passed = all(r[1] for r in results)
    console.print("=" * 60)

    if all_passed:
        console.print("\n[bold green]OK All tests passed![/bold green]\n")
        return 0
    else:
        console.print("\n[bold red]X Some tests failed[/bold red]\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
