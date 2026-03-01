"""Meta Controller: Consciousness Tick System"""
import asyncio
import time
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from enum import Enum
from loguru import logger

from .exploration_policy import ExplorationPolicy
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
    forced_exploration: bool = False
    forced_reason: str = ""


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
    
    def __init__(
        self,
        config: Dict[str, Any],
        left_brain,
        right_brain,
        suggestion_handler: Optional[Callable[[Dict[str, Any]], None]] = None,
        exploration_policy: Optional[ExplorationPolicy] = None,
    ):
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

        self.suggestion_handler = suggestion_handler
        self.exploration_policy = exploration_policy or ExplorationPolicy(config)
        novelty_cfg = config.get("novelty_detection", {}) if isinstance(config, dict) else {}
        self.novelty_detector = NoveltyDetector(novelty_cfg)
        self._lead_history: list = []
        self._forced_exploration_count = 0
        
        self._tick_count = 0
        self._last_tick = time.time()
        self._last_mode_switch = time.time()

        # Adaptive tick interval (starts at configured value)
        self._adaptive_tick_enabled = self.config.get("adaptive_tick", True)
        self._min_tick_interval = self.config.get("min_tick_interval", 0.1)
        self._max_tick_interval = self.config.get("max_tick_interval", 2.0)
        self._current_tick_interval = self.tick_interval

        # Energy/Attention budget
        self._energy_budget_enabled = self.config.get("energy_budget_enabled", True)
        self._max_energy = self.config.get("max_energy", 100.0)
        self._energy_regen_rate = self.config.get("energy_regen_rate", 10.0)  # per second
        self._current_energy = self._max_energy
        self._energy_cost_explore = self.config.get("energy_cost_explore", 15.0)
        self._energy_cost_exploit = self.config.get("energy_cost_exploit", 5.0)
        self._energy_cost_integrate = self.config.get("energy_cost_integrate", 20.0)

        # Multi-metric consciousness state
        self._consciousness_state = {
            "alertness": 1.0,        # 0.0-1.0, affects response speed
            "focus": 0.5,             # 0.0-1.0, affects attention allocation
            "cognitive_load": 0.0,    # 0.0-1.0, current processing burden
            "fatigue": 0.0,           # 0.0-1.0, accumulated over time
            "engagement": 0.5,        # 0.0-1.0, interest in current task
        }
    
    async def start_ticker(self):
        """Start the consciousness tick loop"""
        self.running = True
        logger.info(" Meta-Controller: Consciousness tick system activated")

        while self.running:
            # Use adaptive tick interval if enabled
            tick_interval = self._current_tick_interval if self._adaptive_tick_enabled else self.tick_interval
            await asyncio.sleep(tick_interval)
            await self._tick()
    
    def stop_ticker(self):
        """Stop the consciousness tick loop"""
        self.running = False
        logger.info(" Meta-Controller: Consciousness tick system deactivated")
    
    async def _tick(self):
        """Single consciousness tick - reevaluate state"""
        self._tick_count += 1
        current_time = time.time()
        time_delta = current_time - self._last_tick

        # Regenerate energy based on time elapsed
        if self._energy_budget_enabled:
            self._regenerate_energy(time_delta)

        # Gather state from both hemispheres
        left_state = self.left.get_state_metrics()
        right_state = self.right.get_state_metrics()

        # Calculate meta-metrics
        metrics = self._calculate_metrics(left_state, right_state)

        # Update consciousness state based on metrics
        self._update_consciousness_state(metrics, time_delta)

        # Decide on mode (energy-aware)
        decision, forced, forced_reason = self._decide_mode(metrics)

        # Deduct energy for mode execution
        if self._energy_budget_enabled:
            self._deduct_energy_for_mode(self.mode)

        # Adjust tick interval based on system state
        if self._adaptive_tick_enabled:
            self._adjust_tick_interval(metrics)

        # Record tick
        tick = TickMetrics(
            timestamp=current_time,
            left_entropy=left_state["entropy"],
            right_entropy=right_state["entropy"],
            conflict=metrics["conflict"],
            novelty=metrics["novelty"],
            decision=decision,
            mode=self.mode,
            forced_exploration=forced,
            forced_reason=forced_reason
        )

        self.tick_history.append(tick)
        self._lead_history.append(self._lead_from_mode(self.mode))

        # Log if significant
        if self._is_significant_tick(metrics):
            logger.debug(f" Consciousness Tick #{self._tick_count}: {decision} | Mode: {self.mode.value}")

        self._last_tick = current_time

        if self.suggestion_handler:
            tick_profile = {
                "is_idle": self.mode == CognitiveMode.IDLE,
                "pressure": metrics["entropy"],
                "novelty": metrics["novelty"],
                "conflict": metrics["conflict"],
                "entropy": metrics["entropy"],
            }
            try:
                self.suggestion_handler(tick_profile)
            except Exception:
                logger.debug("Suggestion handler failed")

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
    
    def _decide_mode(self, metrics: Dict[str, float]) -> tuple:
        """Decide which cognitive mode to enter based on metrics"""

        conflict = metrics["conflict"]
        novelty = metrics["novelty"]
        entropy = metrics["entropy"]

        previous_mode = self.mode

        forced = False
        forced_reason = ""

        # Check energy constraints
        energy_level = self.get_energy_level() if self._energy_budget_enabled else 1.0

        # Decision logic
        if entropy > self.thresholds["entropy"]:
            # High uncertainty - need exploration
            if energy_level >= 0.15:  # Need sufficient energy for exploration
                self.mode = CognitiveMode.EXPLORE
                decision = "HIGH_ENTROPY -> EXPLORE"
            else:
                self.mode = CognitiveMode.EXPLOIT  # Fall back to cheaper mode
                decision = "HIGH_ENTROPY -> EXPLOIT (LOW_ENERGY)"

        elif novelty > self.thresholds["novelty"]:
            # High novelty - explore anomalies
            if energy_level >= 0.15:
                self.mode = CognitiveMode.EXPLORE
                decision = "HIGH_NOVELTY -> EXPLORE"
            else:
                self.mode = CognitiveMode.EXPLOIT
                decision = "HIGH_NOVELTY -> EXPLOIT (LOW_ENERGY)"

        elif conflict > self.thresholds["conflict"]:
            # Conflict between brains - integrate
            if energy_level >= 0.20:  # Integration is most expensive
                self.mode = CognitiveMode.INTEGRATE
                decision = "CONFLICT -> INTEGRATE"
            else:
                self.mode = CognitiveMode.EXPLOIT
                decision = "CONFLICT -> EXPLOIT (LOW_ENERGY)"

        else:
            # Low uncertainty - exploit known patterns
            self.mode = CognitiveMode.EXPLOIT
            decision = "STABLE -> EXPLOIT"

        # Forced exploration policy override
        if self.exploration_policy and self.exploration_policy.enabled:
            tick_profile = {
                "pressure": entropy,
                "novelty": novelty,
                "conflict": conflict,
            }
            policy_decision = self.exploration_policy.evaluate(
                tick_profile=tick_profile,
                history=self._lead_history,
                divergence=None,
                tick_count=self._tick_count,
                task_risk=None,
            )
            if policy_decision.force_right_lead:
                self.mode = CognitiveMode.EXPLORE
                decision = f"FORCED_EXPLORATION ({policy_decision.reason})"
                forced = True
                forced_reason = policy_decision.reason
                self._forced_exploration_count += 1
            elif policy_decision.force_right_critic:
                self.mode = CognitiveMode.INTEGRATE
                decision = f"FORCED_RIGHT_CRITIC ({policy_decision.reason})"
                forced = True
                forced_reason = policy_decision.reason
        
        # Track mode switches
        if previous_mode != self.mode:
            self._last_mode_switch = time.time()
            logger.info(f" Mode Switch: {previous_mode.value} -> {self.mode.value}")
        
        return decision, forced, forced_reason

    @staticmethod
    def _lead_from_mode(mode: CognitiveMode) -> str:
        if mode == CognitiveMode.EXPLORE:
            return "right_lead"
        if mode == CognitiveMode.EXPLOIT:
            return "left_lead"
        if mode == CognitiveMode.INTEGRATE:
            return "both"
        return "idle"
    
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

    def _regenerate_energy(self, time_delta: float):
        """Regenerate energy based on time elapsed"""
        energy_regen = self._energy_regen_rate * time_delta
        self._current_energy = min(self._max_energy, self._current_energy + energy_regen)

    def _deduct_energy_for_mode(self, mode: CognitiveMode):
        """Deduct energy based on cognitive mode"""
        cost = 0.0
        if mode == CognitiveMode.EXPLORE:
            cost = self._energy_cost_explore
        elif mode == CognitiveMode.EXPLOIT:
            cost = self._energy_cost_exploit
        elif mode == CognitiveMode.INTEGRATE:
            cost = self._energy_cost_integrate

        self._current_energy = max(0.0, self._current_energy - cost)

    def _update_consciousness_state(self, metrics: Dict[str, float], time_delta: float):
        """Update multi-dimensional consciousness state"""
        # Alertness: decreases with fatigue, increases with novelty
        novelty_boost = metrics["novelty"] * 0.1
        fatigue_penalty = self._consciousness_state["fatigue"] * 0.2
        self._consciousness_state["alertness"] = max(0.0, min(1.0,
            self._consciousness_state["alertness"] + novelty_boost - fatigue_penalty
        ))

        # Focus: increases with stability, decreases with conflict
        stability_factor = metrics["stability"] * 0.1
        conflict_penalty = metrics["conflict"] * 0.15
        self._consciousness_state["focus"] = max(0.0, min(1.0,
            self._consciousness_state["focus"] + stability_factor - conflict_penalty
        ))

        # Cognitive load: based on entropy and conflict
        self._consciousness_state["cognitive_load"] = (metrics["entropy"] + metrics["conflict"]) / 2.0

        # Fatigue: accumulates over time, especially with high cognitive load
        fatigue_rate = 0.01 * time_delta * (1.0 + self._consciousness_state["cognitive_load"])
        self._consciousness_state["fatigue"] = min(1.0,
            self._consciousness_state["fatigue"] + fatigue_rate
        )

        # Engagement: based on novelty and inverse of fatigue
        novelty_engagement = metrics["novelty"] * 0.3
        fatigue_disengagement = self._consciousness_state["fatigue"] * 0.2
        self._consciousness_state["engagement"] = max(0.0, min(1.0,
            0.5 + novelty_engagement - fatigue_disengagement
        ))

    def _adjust_tick_interval(self, metrics: Dict[str, float]):
        """Dynamically adjust tick interval based on system state"""
        # High entropy/conflict/novelty = faster ticking (more attention needed)
        # Low metrics = slower ticking (less attention needed)

        pressure = (metrics["entropy"] + metrics["conflict"] + metrics["novelty"]) / 3.0

        # Inverse relationship: high pressure = short interval (fast ticking)
        # Alertness also affects tick rate
        alertness = self._consciousness_state["alertness"]

        if pressure > 0.7 or alertness > 0.8:
            # High pressure or high alertness: tick faster
            target_interval = self._min_tick_interval
        elif pressure < 0.3 and alertness < 0.5:
            # Low pressure and low alertness: tick slower
            target_interval = self._max_tick_interval
        else:
            # Linear interpolation based on pressure
            # pressure 0.0 -> max_interval, pressure 1.0 -> min_interval
            target_interval = self._max_tick_interval - (pressure * (self._max_tick_interval - self._min_tick_interval))

        # Smooth transition (exponential moving average)
        alpha = 0.3  # Smoothing factor
        self._current_tick_interval = (alpha * target_interval) + ((1 - alpha) * self._current_tick_interval)

    def get_energy_level(self) -> float:
        """Get current energy level (0.0-1.0)"""
        return self._current_energy / self._max_energy

    def get_consciousness_state(self) -> Dict[str, float]:
        """Get current consciousness state metrics"""
        return self._consciousness_state.copy()

    def reset_fatigue(self):
        """Reset fatigue (e.g., after rest period)"""
        self._consciousness_state["fatigue"] = 0.0
        self._consciousness_state["alertness"] = 1.0

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

    def calculate_novelty_tick_rate(
        self,
        expected_outcome: Optional[bool] = None,
        actual_outcome: bool = False,
        confidence: float = 0.5,
        tools_used: Optional[List[str]] = None,
        tool_results: Optional[Dict[str, bool]] = None,
        error_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> float:
        """Calculate tick rate based on novelty signals from execution."""
        return self.novelty_detector.measure_novelty(
            expected_outcome=expected_outcome,
            actual_outcome=actual_outcome,
            confidence=confidence,
            tools_used=tools_used or [],
            tool_results=tool_results or {},
            error_message=error_message,
            context=context or {},
        )

    def calculate_tick_rate_from_trace(
        self,
        trace_data: Dict[str, Any],
        expected_success: Optional[bool] = None,
    ) -> float:
        """Calculate tick rate from an execution trace dictionary."""
        return self.novelty_detector.measure_from_trace(
            trace_data=trace_data,
            expected_success=expected_success,
        )

    def get_current_novelty(self) -> float:
        """Return the moving-average novelty level."""
        return self.novelty_detector.get_current_tick_rate()

    def get_novelty_stats(self) -> Dict[str, Any]:
        """Return novelty detector statistics."""
        return self.novelty_detector.get_stats()
    
    def get_consciousness_metrics(self) -> Dict[str, Any]:
        """Return meta-metrics about consciousness state"""

        return {
            "mode": self.mode.value,
            "tick_count": self._tick_count,
            "tick_rate": self.get_tick_rate(),
            "active_hemisphere": self.get_active_hemisphere(),
            "time_since_last_switch": time.time() - self._last_mode_switch,
            "recent_ticks": len([t for t in self.tick_history if time.time() - t.timestamp < 5.0]),
            "forced_exploration_count": self._forced_exploration_count,
            "current_novelty": self.get_current_novelty(),
            # New metrics
            "energy_level": self.get_energy_level() if self._energy_budget_enabled else 1.0,
            "current_tick_interval": self._current_tick_interval if self._adaptive_tick_enabled else self.tick_interval,
            "consciousness_state": self.get_consciousness_state(),
        }
