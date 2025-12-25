#!/usr/bin/env python3
"""Tests for suggestion delivery pipeline."""

import sys
from pathlib import Path
import shutil

sys.path.insert(0, str(Path(__file__).parent))

from core.memory import ProceduralMemory
from core.memory.suggestion_store import SuggestionStore, Suggestion
from core.memory.suggestion_delivery import SuggestionDelivery


def test_suggestion_delivery() -> None:
    base = Path("./data/memory/test_delivery")
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True, exist_ok=True)
    store_path = base / "suggestions.jsonl"
    if store_path.exists():
        store_path.unlink()

    config = {
        "procedural_memory": {
            "enabled": True,
            "persist_directory": str(base / "procedural"),
            "cross_hemisphere": {
                "enabled": True,
                "mode": "suggestions",
                "suggestions": {
                    "enabled": True,
                    "deliver_when_idle": True,
                    "max_pressure_to_deliver": 0.5,
                    "deliver_budget_per_tick": 2,
                    "expiry_days": 1,
                },
            },
        }
    }

    memory = ProceduralMemory(config)
    store = SuggestionStore(str(store_path))
    delivery = SuggestionDelivery(memory, store, config["procedural_memory"]["cross_hemisphere"])

    suggestion = Suggestion(
        suggestion_id="sg_test",
        from_side="left",
        to_side="right",
        origin_bullet_id="pb_left_123",
        suggested_text="Use retries for transient tool errors",
        tags=["tooling"],
        reason="test",
        status="pending",
        created_at="",
        delivered_at=None,
        resolved_at=None,
        trace_ids=[],
    )
    store.create(suggestion)

    delivered = delivery.deliver_pending({"is_idle": True, "pressure": 0.1})
    assert len(delivered) == 1

    right_bullets = memory.store.list_bullets("right", limit=10)
    assert any(b.metadata.get("suggestion_id") for b in right_bullets)

    # High pressure should block delivery
    suggestion2 = Suggestion(
        suggestion_id="sg_blocked",
        from_side="left",
        to_side="right",
        origin_bullet_id="pb_left_456",
        suggested_text="Check schema before tool execution",
        tags=["schema"],
        reason="test",
        status="pending",
        created_at="",
        delivered_at=None,
        resolved_at=None,
        trace_ids=[],
    )
    store.create(suggestion2)
    blocked = delivery.deliver_pending({"is_idle": True, "pressure": 0.9})
    assert blocked == []


def main() -> int:
    test_suggestion_delivery()
    print("Suggestion delivery tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
