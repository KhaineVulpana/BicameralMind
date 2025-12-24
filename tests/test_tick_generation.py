#!/usr/bin/env python3
"""Test Suite for Tick Generation and Novelty Detection"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.meta_controller import NoveltyDetector, MetaController


def test_novelty_detector_basic():
    """Test basic novelty detection."""
    print("\n=== Test 1: Basic Novelty Detection ===\n")

    detector = NoveltyDetector()

    # Test 1: Routine success (low novelty)
    tick_rate = detector.measure_novelty(
        expected_outcome=True,
        actual_outcome=True,
        confidence=0.9,
        tools_used=["api_call"],
        tool_results={"api_call": True},
    )
    print(f"Routine Success: tick_rate = {tick_rate:.2f} (expected: ~0.1)")
    assert tick_rate < 0.3, "Routine success should have low tick rate"

    # Test 2: Unexpected failure (high novelty)
    tick_rate = detector.measure_novelty(
        expected_outcome=True,
        actual_outcome=False,
        confidence=0.8,
        tools_used=["api_call"],
        tool_results={"api_call": False},
        error_message="Connection timeout",
    )
    print(f"Unexpected Failure: tick_rate = {tick_rate:.2f} (expected: >0.8)")
    assert tick_rate > 0.8, "Unexpected failure should have high tick rate"

    # Test 3: Low confidence task (medium novelty)
    tick_rate = detector.measure_novelty(
        expected_outcome=None,
        actual_outcome=True,
        confidence=0.4,
        tools_used=["complex_query"],
        tool_results={"complex_query": True},
    )
    print(f"Low Confidence: tick_rate = {tick_rate:.2f} (expected: ~0.5-0.7)")
    assert 0.3 < tick_rate < 0.8, "Low confidence should have medium tick rate"

    print("\n[OK] Basic novelty detection tests passed!\n")
    return True


def test_novelty_from_trace():
    """Test novelty detection from execution traces."""
    print("\n=== Test 2: Novelty from Trace ===\n")

    detector = NoveltyDetector()

    # Successful trace
    success_trace = {
        "success": True,
        "confidence": 0.85,
        "tools_called": ["http_client", "json_parser"],
        "steps": [
            {"description": "Validate", "success": True},
            {"description": "Call API", "tool": "http_client", "success": True},
            {"description": "Parse", "tool": "json_parser", "success": True},
        ],
    }

    tick_rate = detector.measure_from_trace(success_trace, expected_success=True)
    print(f"Success Trace: tick_rate = {tick_rate:.2f}")
    assert tick_rate < 0.3, "Successful expected trace should have low tick rate"

    # Failure trace
    failure_trace = {
        "success": False,
        "confidence": 0.3,
        "tools_called": ["payment_api"],
        "error_message": "Payment gateway timeout",
        "steps": [
            {"description": "Validate card", "success": True},
            {"description": "Process payment", "tool": "payment_api", "success": False},
        ],
    }

    tick_rate = detector.measure_from_trace(failure_trace, expected_success=True)
    print(f"Failure Trace: tick_rate = {tick_rate:.2f}")
    assert tick_rate > 0.7, "Failure trace should have high tick rate"

    print("\n[OK] Trace novelty detection tests passed!\n")
    return True


def test_tick_rate_mapping():
    """Test that tick rates map to correct reflection depths."""
    print("\n=== Test 3: Tick Rate Mapping ===\n")

    detector = NoveltyDetector()

    scenarios = [
        ("Very Routine", {"expected_outcome": True, "actual_outcome": True, "confidence": 0.95}, "none", 0.0, 0.15),
        ("Routine", {"expected_outcome": True, "actual_outcome": True, "confidence": 0.7}, "shallow", 0.0, 0.3),
        ("Novel", {"expected_outcome": None, "actual_outcome": True, "confidence": 0.5}, "medium", 0.4, 0.8),
        ("High Novelty", {"expected_outcome": True, "actual_outcome": False, "confidence": 0.4, "error_message": "Failed"}, "deep", 0.8, 1.0),
    ]

    print(f"{'Scenario':<20} {'Tick Rate':<12} {'Expected Depth':<18} {'Status':<10}")
    print("-" * 65)

    for scenario_name, params, expected_depth, min_rate, max_rate in scenarios:
        tick_rate = detector.measure_novelty(**params)
        status = "[OK]" if min_rate <= tick_rate <= max_rate else "[FAIL]"
        print(f"{scenario_name:<20} {tick_rate:6.2f}       {expected_depth:<18} {status:<10}")

        if not (min_rate <= tick_rate <= max_rate):
            print(f"  ERROR: Expected {min_rate:.2f} - {max_rate:.2f}, got {tick_rate:.2f}")
            return False

    print("\n[OK] Tick rate mapping tests passed!\n")
    return True


def test_novelty_moving_average():
    """Test that novelty accumulates and decays properly."""
    print("\n=== Test 4: Novelty Moving Average ===\n")

    detector = NoveltyDetector({"novelty_decay": 0.7})

    # Start with low novelty
    tick1 = detector.measure_novelty(
        expected_outcome=True,
        actual_outcome=True,
        confidence=0.9,
    )
    print(f"Initial (routine): tick_rate = {tick1:.2f}, current_novelty = {detector.current_novelty:.2f}")

    # Add high novelty event
    tick2 = detector.measure_novelty(
        expected_outcome=True,
        actual_outcome=False,
        confidence=0.5,
        error_message="Unexpected failure",
    )
    print(f"After failure: tick_rate = {tick2:.2f}, current_novelty = {detector.current_novelty:.2f}")
    assert detector.current_novelty > 0.3, "Current novelty should increase after failure"

    # Return to routine (novelty should decay)
    for i in range(5):
        detector.measure_novelty(
            expected_outcome=True,
            actual_outcome=True,
            confidence=0.9,
        )

    print(f"After decay: current_novelty = {detector.current_novelty:.2f}")
    assert detector.current_novelty < 0.3, "Novelty should decay after routine tasks"

    print("\n[OK] Moving average tests passed!\n")
    return True


def test_novelty_stats():
    """Test novelty statistics tracking."""
    print("\n=== Test 5: Novelty Statistics ===\n")

    detector = NoveltyDetector()

    # Generate various novelty events
    detector.measure_novelty(expected_outcome=True, actual_outcome=False, error_message="Error 1")
    detector.measure_novelty(expected_outcome=True, actual_outcome=True, confidence=0.3)
    detector.measure_novelty(expected_outcome=True, actual_outcome=False, error_message="Error 2", tools_used=["tool1"], tool_results={"tool1": False})

    stats = detector.get_stats()

    print(f"Total measurements: {stats['total_measurements']}")
    print(f"Current novelty: {stats['current_novelty']:.2f}")
    print(f"Signal counts: {stats['signal_counts']}")

    assert stats['total_measurements'] > 0, "Should have recorded measurements"
    assert 'signal_counts' in stats, "Should have signal counts"

    print("\n[OK] Statistics tests passed!\n")
    return True


def main():
    """Run all tick generation tests."""
    print("\n" + "=" * 75)
    print("Tick Generation Test Suite - Phase 2.5")
    print("=" * 75)

    results = []

    try:
        results.append(("Basic Novelty Detection", test_novelty_detector_basic()))
        results.append(("Novelty from Trace", test_novelty_from_trace()))
        results.append(("Tick Rate Mapping", test_tick_rate_mapping()))
        results.append(("Moving Average", test_novelty_moving_average()))
        results.append(("Novelty Statistics", test_novelty_stats()))

        # Summary
        print("=" * 75)
        print("Test Summary:")
        for test_name, passed in results:
            status = "[OK]" if passed else "[FAIL]"
            print(f"  {status} - {test_name}")

        all_passed = all(r[1] for r in results)
        print("=" * 75)

        if all_passed:
            print("\n[OK] All tests completed successfully!\n")
            return 0
        else:
            print("\n[FAIL] Some tests failed\n")
            return 1

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
