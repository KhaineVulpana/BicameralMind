"""Meta Controller: Consciousness Tick System"""
import asyncio
import time
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from loguru import logger

from .exploration_policy import ExplorationPolicy


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
        self._lead_history: list = []
        self._forced_exploration_count = 0
        
        self._tick_count = 0
        self._last_tick = time.time()
        self._last_mode_switch = time.time()
    
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
        decision, forced, forced_reason = self._decide_mode(metrics)
        
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
            logger.debug(f"⚡ Consciousness Tick #{self._tick_count}: {decision} | Mode: {self.mode.value}")
        
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

        # Decision logic
        if entropy > self.thresholds["entropy"]:
            # High uncertainty - need exploration
            self.mode = CognitiveMode.EXPLORE
            decision = "HIGH_ENTROPY -> EXPLORE"
        
        elif novelty > self.thresholds["novelty"]:
            # High novelty - explore anomalies
            self.mode = CognitiveMode.EXPLORE
            decision = "HIGH_NOVELTY -> EXPLORE"
        
        elif conflict > self.thresholds["conflict"]:
            # Conflict between brains - integrate
            self.mode = CognitiveMode.INTEGRATE
            decision = "CONFLICT -> INTEGRATE"
        
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
            logger.info(f"🔄 Mode Switch: {previous_mode.value} → {self.mode.value}")
        
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
            "recent_ticks": len([t for t in self.tick_history if time.time() - t.timestamp < 5.0]),
            "forced_exploration_count": self._forced_exploration_count,
        }
