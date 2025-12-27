#!/usr/bin/env python3
"""Tests for MetaController novelty integration."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.meta_controller import MetaController


class DummyBrain:
    def __init__(self, confidence: float, entropy: float):
        self._confidence = confidence
        self._entropy = entropy

    def get_state_metrics(self):
        return {
            "confidence": self._confidence,
            "entropy": self._entropy,
            "memory_load": 0.1,
        }


def test_novelty_helpers() -> None:
    config = {
        "novelty_detection": {"novelty_decay": 0.8},
        "bicameral": {
            "tick_interval": 0.5,
            "tick_threshold": {"entropy": 0.6, "conflict": 0.5, "novelty": 0.7},
        },
        "procedural_memory": {"cross_hemisphere": {"exploration": {"enabled": False}}},
    }
    meta = MetaController(config, DummyBrain(0.6, 0.4), DummyBrain(0.5, 0.3))

    tick_rate = meta.calculate_novelty_tick_rate(
        expected_outcome=True,
        actual_outcome=False,
        confidence=0.4,
        tools_used=["filesystem.read_file"],
        tool_results={"filesystem.read_file": False},
        error_message="timeout",
        context={"task": "test"},
    )
    assert 0.0 <= tick_rate <= 1.0

    trace_tick = meta.calculate_tick_rate_from_trace(
        {
            "success": False,
            "confidence": 0.4,
            "tools_called": ["filesystem.read_file"],
            "steps": [{"tool": "filesystem.read_file", "success": False}],
            "error_message": "timeout",
        },
        expected_success=True,
    )
    assert 0.0 <= trace_tick <= 1.0

    current = meta.get_current_novelty()
    stats = meta.get_novelty_stats()
    assert isinstance(current, float)
    assert "current_novelty" in stats


def main() -> int:
    test_novelty_helpers()
    print("MetaController novelty integration tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
