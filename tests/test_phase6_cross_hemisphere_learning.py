#!/usr/bin/env python3
"""Minimal tests for Phase 6 cross-hemisphere learning components."""

import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.memory import (
    Bullet,
    BulletType,
    BulletStatus,
    Hemisphere,
    SuggestionStore,
    Suggestion,
    TeachingAPI,
    ConflictDetector,
    DiversityMetrics,
)
from core.meta_controller import ExplorationPolicy


def test_suggestion_store(tmp_path: Path) -> None:
    store = SuggestionStore(str(tmp_path))
    suggestion_id = store.create(
        Suggestion(
            suggestion_id="",
            from_side="left",
            to_side="right",
            origin_bullet_id="pb_left_1",
            suggested_text="Use retries for tool calls",
            tags=["tooling"],
            reason="test",
            status="pending",
            created_at="",
            delivered_at=None,
            resolved_at=None,
            trace_ids=[],
        )
    )
    assert suggestion_id
    assert len(store.list_pending("right")) == 1
    store.mark_delivered(suggestion_id, delivered_bullet_id="pb_right_1")
    store.resolve(suggestion_id, accepted=True, reason="ok")

    old_id = store.create(
        Suggestion(
            suggestion_id="sg_old",
            from_side="left",
            to_side="right",
            origin_bullet_id="pb_left_2",
            suggested_text="Old suggestion",
            tags=[],
            reason="old",
            status="pending",
            created_at=(datetime.utcnow() - timedelta(days=30)).isoformat(timespec="seconds") + "Z",
            delivered_at=None,
            resolved_at=None,
            trace_ids=[],
        )
    )
    assert old_id
    expired = store.expire_old(7)
    assert expired >= 1


def test_teaching_api(tmp_path: Path) -> None:
    config = {"procedural_memory": {"enabled": False, "cross_hemisphere": {"enabled": True}}}
    from core.memory import ProceduralMemory

    memory = ProceduralMemory(config)
    store = SuggestionStore(str(tmp_path))
    teacher = TeachingAPI(memory, store)
    suggestion_id = teacher.teach_text(
        from_side="left",
        to_side="right",
        text="Prefer dry-run before destructive actions",
        tags=["safety"],
        translate=True,
    )
    assert suggestion_id
    pending = store.list_pending("right")
    assert len(pending) == 1


def test_conflict_detector() -> None:
    detector = ConflictDetector()
    a = Bullet.create(
        text="Must enable retries for tool calls in network operations always",
        side=Hemisphere.LEFT,
        bullet_type=BulletType.HEURISTIC,
        tags=["tooling"],
    )
    a.status = BulletStatus.ACTIVE
    b = Bullet.create(
        text="Must not enable retries for tool calls in network operations always",
        side=Hemisphere.RIGHT,
        bullet_type=BulletType.HEURISTIC,
        tags=["tooling"],
    )
    b.status = BulletStatus.ACTIVE
    conflicts = detector.find_conflicts(a, [b])
    assert len(conflicts) == 1


def test_diversity_metrics() -> None:
    metrics = DiversityMetrics()
    left = [
        Bullet.create("Left bullet A", Hemisphere.LEFT, BulletType.HEURISTIC, tags=["a"]),
        Bullet.create("Left bullet B", Hemisphere.LEFT, BulletType.HEURISTIC, tags=["b"]),
    ]
    right = [
        Bullet.create("Right bullet A", Hemisphere.RIGHT, BulletType.HEURISTIC, tags=["a"]),
        Bullet.create("Right bullet B", Hemisphere.RIGHT, BulletType.HEURISTIC, tags=["b"]),
    ]
    divergence = metrics.tag_divergence(left, right)
    assert divergence < 1e-6


def test_exploration_policy() -> None:
    config = {
        "procedural_memory": {
            "cross_hemisphere": {
                "exploration": {
                    "enabled": True,
                    "mode": "quota",
                    "window_size": 4,
                    "min_right_fraction": 0.5,
                },
                "diversity": {
                    "convergence_warning_threshold": 0.15,
                },
            }
        }
    }
    policy = ExplorationPolicy(config)
    history = ["left_lead", "left_lead", "left_lead", "left_lead"]
    decision = policy.evaluate(tick_profile={}, history=history, tick_count=5)
    assert decision.force_right_lead


def main() -> int:
    base = Path("./data/memory")
    base.mkdir(parents=True, exist_ok=True)
    store_path = base / "test_phase6_suggestions.jsonl"
    teach_path = base / "test_phase6_teaching.jsonl"

    for path in (store_path, teach_path):
        if path.exists():
            path.unlink()

    test_suggestion_store(store_path)
    test_teaching_api(teach_path)
    test_conflict_detector()
    test_diversity_metrics()
    test_exploration_policy()

    print("Phase 6 tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
