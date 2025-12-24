"""Meta Controller: Consciousness Tick System"""
import asyncio
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
from loguru import logger
from .novelty_detector import NoveltyDetector


class CognitiveMode(Enum):
    EXPLORE = "explore"      # Right brain dominant
    EXPLOIT = "exploit"      # Left brain dominant
    INTEGRATE = "integrate"  # Both active
    IDLE = "idle"


@dataclass
class TickMetrics:
    """Metrics captured at each consciousness tick"""
    timestamp: float
    left_entropy: float
    right_entropy: float
    conflict: float
    novelty: float
    decision: str
    mode: CognitiveMode


class MetaController:
    """
    Meta-Controller: Consciousness Tick System
    
    Responsibility:
    - Periodic reevaluation (consciousness ticks)
    - Mode switching (explore vs exploit)
    - Conflict detection and resolution
    - Attention allocation
    - Meta-awareness: "What am I doing? Should I switch?"
    """
    
    def __init__(self, config: Dict[str, Any], left_brain, right_brain):
        self.config = config.get("bicameral", {})
        self.left = left_brain
        self.right = right_brain

        self.tick_interval = self.config.get("tick_interval", 0.5)
        self.thresholds = self.config.get("tick_threshold", {
            "entropy": 0.6,
            "conflict": 0.5,
            "novelty": 0.7
        })

        self.mode = CognitiveMode.IDLE
        self.tick_history = []
        self.running = False

        self._tick_count = 0
        self._last_tick = time.time()
        self._last_mode_switch = time.time()

        # Novelty detector for learning-oriented tick generation
        self.novelty_detector = NoveltyDetector(config.get("novelty_detection", {}))
    
    async def start_ticker(self):
        """Start the consciousness tick loop"""
        self.running = True
        logger.info("🧠 Meta-Controller: Consciousness tick system activated")
        
        while self.running:
            await asyncio.sleep(self.tick_interval)
            await self._tick()
    
    def stop_ticker(self):
        """Stop the consciousness tick loop"""
        self.running = False
        logger.info("🧠 Meta-Controller: Consciousness tick system deactivated")
    
    async def _tick(self):
        """Single consciousness tick - reevaluate state"""
        self._tick_count += 1
        current_time = time.time()
        
        # Gather state from both hemispheres
        left_state = self.left.get_state_metrics()
        right_state = self.right.get_state_metrics()
        
        # Calculate meta-metrics
        metrics = self._calculate_metrics(left_state, right_state)
        
        # Decide on mode
        decision = self._decide_mode(metrics)
        
        # Record tick
        tick = TickMetrics(
            timestamp=current_time,
            left_entropy=left_state["entropy"],
            right_entropy=right_state["entropy"],
            conflict=metrics["conflict"],
            novelty=metrics["novelty"],
            decision=decision,
            mode=self.mode
        )
        
        self.tick_history.append(tick)
        
        # Log if significant
        if self._is_significant_tick(metrics):
            logger.debug(f"⚡ Consciousness Tick #{self._tick_count}: {decision} | Mode: {self.mode.value}")
        
        self._last_tick = current_time
        
        return tick
    
    def _calculate_metrics(self, left: Dict[str, float], right: Dict[str, float]) -> Dict[str, float]:
        """Calculate meta-level metrics from brain states"""
        
        # Conflict: disagreement between hemispheres
        conflict = abs(left["confidence"] - right["confidence"])
        
        # Novelty: how much the right brain is surprised
        novelty = right["entropy"]
        
        # Entropy average
        avg_entropy = (left["entropy"] + right["entropy"]) / 2
        
        # Stability: inverse of entropy
        stability = 1.0 - avg_entropy
        
        return {
            "conflict": conflict,
            "novelty": novelty,
            "entropy": avg_entropy,
            "stability": stability,
            "left_conf": left["confidence"],
            "right_conf": right["confidence"]
        }
    
    def _decide_mode(self, metrics: Dict[str, float]) -> str:
        """Decide which cognitive mode to enter based on metrics"""
        
        conflict = metrics["conflict"]
        novelty = metrics["novelty"]
        entropy = metrics["entropy"]
        
        previous_mode = self.mode
        
        # Decision logic
        if entropy > self.thresholds["entropy"]:
            # High uncertainty - need exploration
            self.mode = CognitiveMode.EXPLORE
            decision = "HIGH_ENTROPY → EXPLORE"
        
        elif novelty > self.thresholds["novelty"]:
            # High novelty - explore anomalies
            self.mode = CognitiveMode.EXPLORE
            decision = "HIGH_NOVELTY → EXPLORE"
        
        elif conflict > self.thresholds["conflict"]:
            # Conflict between brains - integrate
            self.mode = CognitiveMode.INTEGRATE
            decision = "CONFLICT → INTEGRATE"
        
        else:
            # Low uncertainty - exploit known patterns
            self.mode = CognitiveMode.EXPLOIT
            decision = "STABLE → EXPLOIT"
        
        # Track mode switches
        if previous_mode != self.mode:
            self._last_mode_switch = time.time()
            logger.info(f"🔄 Mode Switch: {previous_mode.value} → {self.mode.value}")
        
        return decision
    
    def _is_significant_tick(self, metrics: Dict[str, float]) -> bool:
        """Check if this tick represents a significant state change"""
        
        # Significant if:
        # - High conflict
        # - High novelty
        # - Recent mode switch
        
        recent_switch = (time.time() - self._last_mode_switch) < 2.0
        
        return (
            metrics["conflict"] > self.thresholds["conflict"] or
            metrics["novelty"] > self.thresholds["novelty"] or
            recent_switch
        )
    
    def get_active_hemisphere(self) -> Optional[str]:
        """Determine which hemisphere should be primary based on mode"""
        
        if self.mode == CognitiveMode.EXPLORE:
            return "right"
        elif self.mode == CognitiveMode.EXPLOIT:
            return "left"
        elif self.mode == CognitiveMode.INTEGRATE:
            return "both"
        else:
            return None
    
    def get_tick_rate(self, window: float = 10.0) -> float:
        """Calculate tick rate over recent window (consciousness frequency)"""
        
        current_time = time.time()
        recent_ticks = [
            t for t in self.tick_history 
            if current_time - t.timestamp <= window
        ]
        
        if recent_ticks:
            return len(recent_ticks) / window
        return 0.0
    
    def get_consciousness_metrics(self) -> Dict[str, Any]:
        """Return meta-metrics about consciousness state"""

        return {
            "mode": self.mode.value,
            "tick_count": self._tick_count,
            "tick_rate": self.get_tick_rate(),
            "active_hemisphere": self.get_active_hemisphere(),
            "time_since_last_switch": time.time() - self._last_mode_switch,
            "recent_ticks": len([t for t in self.tick_history if time.time() - t.timestamp < 5.0])
        }

    # ========================================================================
    # Novelty-Based Tick Generation (for Learning Pipeline)
    # ========================================================================

    def calculate_novelty_tick_rate(
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
        Calculate tick rate based on novelty/surprise in execution.

        This is the primary method for generating consciousness ticks
        for the learning pipeline.

        Returns:
            tick_rate (0.0 - 1.0): Higher = more novel = deeper reflection
        """

        return self.novelty_detector.measure_novelty(
            expected_outcome=expected_outcome,
            actual_outcome=actual_outcome,
            confidence=confidence,
            tools_used=tools_used,
            tool_results=tool_results,
            error_message=error_message,
            context=context,
        )

    def calculate_tick_rate_from_trace(
        self,
        trace_data: Dict[str, Any],
        expected_success: Optional[bool] = None,
    ) -> float:
        """
        Calculate tick rate from an execution trace dictionary.

        Convenience method for learning pipeline integration.

        Args:
            trace_data: Execution trace with keys: success, confidence,
                       tools_called, steps, error_message, etc.
            expected_success: Optional expected outcome for comparison

        Returns:
            tick_rate (0.0 - 1.0): Novelty-based consciousness tick rate
        """

        return self.novelty_detector.measure_from_trace(
            trace_data=trace_data,
            expected_success=expected_success,
        )

    def get_current_novelty(self) -> float:
        """Get current novelty level (moving average)."""
        return self.novelty_detector.get_current_tick_rate()

    def get_novelty_stats(self) -> Dict[str, Any]:
        """Get detailed novelty detection statistics."""
        return self.novelty_detector.get_stats()
