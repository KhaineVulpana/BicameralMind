"""Test Meta-Controller Enhancements: Adaptive Ticks, Energy Budget, Consciousness State.

Verifies:
1. Adaptive tick interval adjusts based on system pressure
2. Energy budget management (deduction and regeneration)
3. Multi-metric consciousness state tracking (alertness, focus, load, fatigue, engagement)
"""

import pytest
import asyncio
import time
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.meta_controller.controller import MetaController, CognitiveMode


class MockBrain:
    """Mock brain for testing"""

    def __init__(self, entropy=0.5, confidence=0.7):
        self.entropy = entropy
        self.confidence = confidence

    def get_state_metrics(self):
        return {
            "entropy": self.entropy,
            "confidence": self.confidence
        }


@pytest.fixture
def config():
    """Configuration with enhancements enabled"""
    return {
        "bicameral": {
            "tick_interval": 0.5,
            "tick_threshold": {
                "entropy": 0.6,
                "conflict": 0.5,
                "novelty": 0.7
            },
            # Adaptive tick
            "adaptive_tick": True,
            "min_tick_interval": 0.1,
            "max_tick_interval": 2.0,
            # Energy budget
            "energy_budget_enabled": True,
            "max_energy": 100.0,
            "energy_regen_rate": 10.0,
            "energy_cost_explore": 15.0,
            "energy_cost_exploit": 5.0,
            "energy_cost_integrate": 20.0
        }
    }


@pytest.fixture
def meta_controller(config):
    """Create meta-controller with mock brains"""
    left = MockBrain(entropy=0.3, confidence=0.8)
    right = MockBrain(entropy=0.4, confidence=0.6)
    return MetaController(config, left, right)


def test_initialization(meta_controller):
    """Test that all enhancement features are initialized"""
    # Adaptive tick
    assert meta_controller._adaptive_tick_enabled == True
    assert meta_controller._min_tick_interval == 0.1
    assert meta_controller._max_tick_interval == 2.0
    assert meta_controller._current_tick_interval == 0.5

    # Energy budget
    assert meta_controller._energy_budget_enabled == True
    assert meta_controller._max_energy == 100.0
    assert meta_controller._current_energy == 100.0
    assert meta_controller._energy_cost_explore == 15.0

    # Consciousness state
    assert "alertness" in meta_controller._consciousness_state
    assert "focus" in meta_controller._consciousness_state
    assert "cognitive_load" in meta_controller._consciousness_state
    assert "fatigue" in meta_controller._consciousness_state
    assert "engagement" in meta_controller._consciousness_state

    print("[OK] All enhancements initialized correctly")


def test_energy_regeneration(meta_controller):
    """Test energy regeneration over time"""
    # Deplete some energy
    meta_controller._current_energy = 50.0

    # Simulate 2 seconds passing
    meta_controller._regenerate_energy(2.0)

    # Should regenerate 10.0 per second * 2 seconds = 20.0
    # 50.0 + 20.0 = 70.0
    assert meta_controller._current_energy == 70.0

    # Test cap at max_energy
    meta_controller._current_energy = 95.0
    meta_controller._regenerate_energy(1.0)
    assert meta_controller._current_energy == 100.0  # Capped

    print("[OK] Energy regeneration works correctly")


def test_energy_deduction(meta_controller):
    """Test energy deduction for different modes"""
    # Start with full energy
    meta_controller._current_energy = 100.0

    # EXPLORE mode costs 15.0
    meta_controller._deduct_energy_for_mode(CognitiveMode.EXPLORE)
    assert meta_controller._current_energy == 85.0

    # EXPLOIT mode costs 5.0
    meta_controller._deduct_energy_for_mode(CognitiveMode.EXPLOIT)
    assert meta_controller._current_energy == 80.0

    # INTEGRATE mode costs 20.0
    meta_controller._deduct_energy_for_mode(CognitiveMode.INTEGRATE)
    assert meta_controller._current_energy == 60.0

    # Test floor at 0
    meta_controller._current_energy = 3.0
    meta_controller._deduct_energy_for_mode(CognitiveMode.EXPLORE)
    assert meta_controller._current_energy == 0.0

    print("[OK] Energy deduction works correctly")


def test_consciousness_state_updates(meta_controller):
    """Test consciousness state tracking"""
    # Initial state
    initial_alertness = meta_controller._consciousness_state["alertness"]

    # Create high-pressure metrics
    metrics = {
        "novelty": 0.8,
        "entropy": 0.7,
        "conflict": 0.6,
        "stability": 0.3
    }

    # Update state
    meta_controller._update_consciousness_state(metrics, time_delta=1.0)

    # Alertness should increase due to novelty
    assert meta_controller._consciousness_state["alertness"] >= initial_alertness

    # Cognitive load should be high
    assert meta_controller._consciousness_state["cognitive_load"] > 0.5

    # Fatigue should accumulate
    assert meta_controller._consciousness_state["fatigue"] > 0.0

    # Focus should decrease due to conflict
    assert meta_controller._consciousness_state["focus"] < 1.0

    print("[OK] Consciousness state tracking works correctly")


def test_adaptive_tick_interval(meta_controller):
    """Test adaptive tick interval adjustment"""
    # Initial interval
    initial_interval = meta_controller._current_tick_interval

    # High pressure metrics -> should decrease interval (faster ticks)
    high_pressure_metrics = {
        "entropy": 0.9,
        "conflict": 0.8,
        "novelty": 0.9,
        "stability": 0.1
    }

    meta_controller._adjust_tick_interval(high_pressure_metrics)
    assert meta_controller._current_tick_interval < initial_interval

    # Low pressure metrics -> should increase interval (slower ticks)
    low_pressure_metrics = {
        "entropy": 0.1,
        "conflict": 0.1,
        "novelty": 0.1,
        "stability": 0.9
    }

    meta_controller._consciousness_state["alertness"] = 0.3  # Low alertness
    meta_controller._adjust_tick_interval(low_pressure_metrics)
    assert meta_controller._current_tick_interval > 0.5

    print("[OK] Adaptive tick interval works correctly")


def test_energy_constrained_mode_selection(meta_controller):
    """Test that low energy forces cheaper modes"""
    # Deplete energy
    meta_controller._current_energy = 10.0  # Only 10% energy

    # High entropy should normally trigger EXPLORE, but energy is too low
    metrics = {
        "entropy": 0.9,
        "conflict": 0.2,
        "novelty": 0.3,
        "stability": 0.1,
        "left_conf": 0.5,
        "right_conf": 0.5
    }

    decision, forced, reason = meta_controller._decide_mode(metrics)

    # Should fall back to EXPLOIT due to low energy
    assert meta_controller.mode == CognitiveMode.EXPLOIT
    assert "LOW_ENERGY" in decision

    print("[OK] Energy-constrained mode selection works correctly")


def test_get_consciousness_metrics(meta_controller):
    """Test that consciousness metrics are exposed"""
    metrics = meta_controller.get_consciousness_metrics()

    # Should include new metrics
    assert "energy_level" in metrics
    assert "current_tick_interval" in metrics
    assert "consciousness_state" in metrics

    # Energy level should be 0.0-1.0
    assert 0.0 <= metrics["energy_level"] <= 1.0

    # Consciousness state should have all dimensions
    state = metrics["consciousness_state"]
    assert "alertness" in state
    assert "focus" in state
    assert "cognitive_load" in state
    assert "fatigue" in state
    assert "engagement" in state

    print("[OK] Consciousness metrics exposed correctly")


def test_reset_fatigue(meta_controller):
    """Test fatigue reset functionality"""
    # Set high fatigue
    meta_controller._consciousness_state["fatigue"] = 0.8
    meta_controller._consciousness_state["alertness"] = 0.3

    # Reset
    meta_controller.reset_fatigue()

    # Should be back to optimal
    assert meta_controller._consciousness_state["fatigue"] == 0.0
    assert meta_controller._consciousness_state["alertness"] == 1.0

    print("[OK] Fatigue reset works correctly")


@pytest.mark.asyncio
async def test_full_tick_cycle(meta_controller):
    """Test complete tick cycle with all enhancements"""
    # Set initial state
    meta_controller._current_energy = 100.0
    meta_controller._last_tick = time.time() - 1.0  # 1 second ago

    # Mock high-entropy brain states
    meta_controller.left.entropy = 0.8
    meta_controller.right.entropy = 0.9

    # Run a tick
    tick = await meta_controller._tick()

    # Verify tick was recorded
    assert tick is not None
    assert tick.mode in [CognitiveMode.EXPLORE, CognitiveMode.EXPLOIT, CognitiveMode.INTEGRATE, CognitiveMode.IDLE]

    # Energy should have been affected (regen - cost)
    # Started at 100, should have regenerated some (10/sec * time_delta)
    # Then deducted cost for mode
    energy_level = meta_controller.get_energy_level()
    assert 0.0 <= energy_level <= 1.0

    # Tick interval should have been adjusted
    assert meta_controller._current_tick_interval != 0.5

    # Consciousness state should have been updated
    assert meta_controller._consciousness_state["fatigue"] > 0.0

    print("[OK] Full tick cycle works with all enhancements")


if __name__ == "__main__":
    print("\n=== META-CONTROLLER ENHANCEMENTS TESTS ===\n")

    # Create test fixtures
    config = {
        "bicameral": {
            "tick_interval": 0.5,
            "tick_threshold": {
                "entropy": 0.6,
                "conflict": 0.5,
                "novelty": 0.7
            },
            "adaptive_tick": True,
            "min_tick_interval": 0.1,
            "max_tick_interval": 2.0,
            "energy_budget_enabled": True,
            "max_energy": 100.0,
            "energy_regen_rate": 10.0,
            "energy_cost_explore": 15.0,
            "energy_cost_exploit": 5.0,
            "energy_cost_integrate": 20.0
        }
    }

    left = MockBrain(entropy=0.3, confidence=0.8)
    right = MockBrain(entropy=0.4, confidence=0.6)
    meta = MetaController(config, left, right)

    # Run tests
    test_initialization(meta)
    test_energy_regeneration(meta)
    test_energy_deduction(meta)
    test_consciousness_state_updates(meta)
    test_adaptive_tick_interval(meta)
    test_energy_constrained_mode_selection(meta)
    test_get_consciousness_metrics(meta)
    test_reset_fatigue(meta)
    asyncio.run(test_full_tick_cycle(meta))

    print("\n[PASS] All meta-controller enhancement tests passed!")
