"""Novelty Detection for Consciousness Tick Generation

This module calculates novelty/surprise signals that drive consciousness ticks.
High novelty → High tick rate → Deeper reflection → More learning
Low novelty → Low tick rate → Shallow/no reflection → Efficiency
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from enum import Enum
import time
from loguru import logger


class NoveltySignal(str, Enum):
    """Types of novelty signals that drive consciousness"""
    PREDICTION_ERROR = "prediction_error"      # Expected != Actual
    TOOL_FAILURE = "tool_failure"              # Tool unexpectedly failed
    LOW_CONFIDENCE = "low_confidence"          # Agent uncertain
    PATTERN_VIOLATION = "pattern_violation"    # Right brain detects anomaly
    EXECUTION_ERROR = "execution_error"        # Task failed
    UNEXPECTED_SUCCESS = "unexpected_success"  # Surprising win
    NOVEL_SITUATION = "novel_situation"        # Never seen before


@dataclass
class NoveltyMeasurement:
    """A single novelty measurement from execution"""
    signal_type: NoveltySignal
    magnitude: float  # 0.0 - 1.0
    timestamp: float
    context: Dict[str, Any]
    evidence: str


class NoveltyDetector:
    """
    Detects novelty/surprise in task execution to generate consciousness ticks.

    Novelty Sources:
    1. Prediction errors (expected != actual)
    2. Tool failures (especially unexpected)
    3. Low confidence (agent is unsure)
    4. Pattern violations (right brain surprise)
    5. Execution failures
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

        # Decay factor for recent novelty (exponential moving average)
        self.decay_factor = self.config.get("novelty_decay", 0.8)

        # History of recent novelty measurements
        self.novelty_history: List[NoveltyMeasurement] = []

        # Current novelty level (moving average)
        self.current_novelty = 0.0

        # Baseline expectations (learned over time)
        self.baseline_confidence = 0.7
        self.baseline_success_rate = 0.8

        logger.debug("🔍 NoveltyDetector initialized")

    def measure_novelty(
        self,
        expected_outcome: Optional[bool] = None,
        actual_outcome: bool = False,
        confidence: float = 0.5,
        tools_used: List[str] = None,
        tool_results: Dict[str, bool] = None,
        error_message: Optional[str] = None,
        context: Dict[str, Any] = None,
    ) -> float:
        """
        Measure novelty from a task execution.

        Returns tick_rate (0.0 - 1.0) based on accumulated novelty signals.
        """

        tools_used = tools_used or []
        tool_results = tool_results or {}
        context = context or {}

        measurements: List[NoveltyMeasurement] = []

        # 1. Prediction Error
        if expected_outcome is not None and expected_outcome != actual_outcome:
            # Unexpected outcome
            magnitude = 0.8 if not actual_outcome else 0.6  # Failures more novel than successes
            measurements.append(NoveltyMeasurement(
                signal_type=NoveltySignal.PREDICTION_ERROR,
                magnitude=magnitude,
                timestamp=time.time(),
                context=context,
                evidence=f"Expected {expected_outcome}, got {actual_outcome}"
            ))

        # 2. Execution Failure
        if not actual_outcome:
            # Task failed
            magnitude = 0.9  # Failures are highly novel
            measurements.append(NoveltyMeasurement(
                signal_type=NoveltySignal.EXECUTION_ERROR,
                magnitude=magnitude,
                timestamp=time.time(),
                context={"error": error_message},
                evidence=f"Task failed: {error_message or 'Unknown error'}"
            ))

        # 3. Low Confidence
        if confidence < self.baseline_confidence:
            # Agent is uncertain
            magnitude = 1.0 - confidence  # Lower confidence = higher novelty
            measurements.append(NoveltyMeasurement(
                signal_type=NoveltySignal.LOW_CONFIDENCE,
                magnitude=magnitude,
                timestamp=time.time(),
                context={"confidence": confidence},
                evidence=f"Low confidence: {confidence:.2f} < {self.baseline_confidence:.2f}"
            ))

        # 4. Tool Failures
        for tool_name, success in tool_results.items():
            if not success:
                measurements.append(NoveltyMeasurement(
                    signal_type=NoveltySignal.TOOL_FAILURE,
                    magnitude=0.7,
                    timestamp=time.time(),
                    context={"tool": tool_name},
                    evidence=f"Tool '{tool_name}' failed"
                ))

        # 5. Unexpected Success (low confidence but succeeded)
        if actual_outcome and confidence < 0.4:
            measurements.append(NoveltyMeasurement(
                signal_type=NoveltySignal.UNEXPECTED_SUCCESS,
                magnitude=0.5,
                timestamp=time.time(),
                context={"confidence": confidence},
                evidence=f"Unexpected success with confidence {confidence:.2f}"
            ))

        # Add measurements to history
        self.novelty_history.extend(measurements)

        # Calculate tick rate from novelty signals
        tick_rate = self._calculate_tick_rate(measurements)

        # Update current novelty (exponential moving average)
        self.current_novelty = (
            self.decay_factor * self.current_novelty +
            (1 - self.decay_factor) * tick_rate
        )

        # Log if significant
        if tick_rate > 0.5:
            logger.debug(
                f"🔍 High novelty detected: tick_rate={tick_rate:.2f} "
                f"({len(measurements)} signals)"
            )

        return tick_rate

    def _calculate_tick_rate(self, measurements: List[NoveltyMeasurement]) -> float:
        """
        Convert novelty measurements to a tick rate (0.0 - 1.0).

        Tick Rate Mapping:
        - 0.0 - 0.2: Very routine (no/shallow reflection)
        - 0.2 - 0.5: Routine (shallow reflection)
        - 0.5 - 0.8: Novel (medium reflection)
        - 0.8 - 1.0: Highly novel (deep reflection)
        """

        if not measurements:
            # No novelty signals - routine task
            return 0.1

        # Calculate weighted average of novelty magnitudes
        total_magnitude = sum(m.magnitude for m in measurements)
        avg_magnitude = total_magnitude / len(measurements)

        # Boost if multiple signals
        signal_boost = min(len(measurements) * 0.1, 0.3)

        # Combine
        tick_rate = min(avg_magnitude + signal_boost, 1.0)

        return tick_rate

    def measure_from_trace(
        self,
        trace_data: Dict[str, Any],
        expected_success: Optional[bool] = None,
    ) -> float:
        """
        Measure novelty from an execution trace dictionary.

        Convenience method for integration with existing trace structures.
        """

        # Extract relevant fields
        actual_outcome = trace_data.get("success", False)
        confidence = trace_data.get("confidence", 0.5)
        tools_used = trace_data.get("tools_called", [])
        error_message = trace_data.get("error_message")

        # Extract tool results from steps
        tool_results = {}
        steps = trace_data.get("steps", [])
        for step in steps:
            if "tool" in step:
                tool_results[step["tool"]] = step.get("success", False)

        # Measure novelty
        return self.measure_novelty(
            expected_outcome=expected_success,
            actual_outcome=actual_outcome,
            confidence=confidence,
            tools_used=tools_used,
            tool_results=tool_results,
            error_message=error_message,
            context=trace_data,
        )

    def get_current_tick_rate(self) -> float:
        """Get the current tick rate (moving average)."""
        return self.current_novelty

    def reset(self):
        """Reset novelty tracking (useful for testing)."""
        self.novelty_history.clear()
        self.current_novelty = 0.0
        logger.debug("🔍 NoveltyDetector reset")

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about novelty detection."""

        recent_time = time.time() - 60.0  # Last minute
        recent_measurements = [
            m for m in self.novelty_history
            if m.timestamp > recent_time
        ]

        signal_counts = {}
        for m in recent_measurements:
            signal_type = m.signal_type.value
            signal_counts[signal_type] = signal_counts.get(signal_type, 0) + 1

        return {
            "current_novelty": self.current_novelty,
            "total_measurements": len(self.novelty_history),
            "recent_measurements": len(recent_measurements),
            "signal_counts": signal_counts,
            "baseline_confidence": self.baseline_confidence,
            "baseline_success_rate": self.baseline_success_rate,
        }
