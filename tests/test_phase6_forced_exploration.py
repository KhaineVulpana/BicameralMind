#!/usr/bin/env python3
"""Tests for forced exploration policy."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.meta_controller import ExplorationPolicy


def test_quota_trigger() -> None:
    config = {
        "procedural_memory": {
            "cross_hemisphere": {
                "exploration": {
                    "enabled": True,
                    "mode": "quota",
                    "window_size": 4,
                    "min_right_fraction": 0.5,
                }
            }
        }
    }
    policy = ExplorationPolicy(config)
    history = ["left_lead", "left_lead", "left_lead", "left_lead"]
    decision = policy.evaluate(tick_profile={}, history=history, tick_count=4)
    assert decision.force_right_lead


def test_interval_trigger() -> None:
    config = {
        "procedural_memory": {
            "cross_hemisphere": {
                "exploration": {
                    "enabled": True,
                    "mode": "interval",
                    "interval_ticks": 3,
                }
            }
        }
    }
    policy = ExplorationPolicy(config)
    decision = policy.evaluate(tick_profile={}, history=[], tick_count=3)
    assert decision.force_right_lead


def main() -> int:
    test_quota_trigger()
    test_interval_trigger()
    print("Forced exploration tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
