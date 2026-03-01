"""Forced exploration policy for meta-controller."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.memory.config_utils import get_cross_hemisphere_config


@dataclass
class ExplorationDecision:
    force_right_lead: bool = False
    force_right_critic: bool = False
    reason: str = ""


class ExplorationPolicy:
    """Decide when to force right-hemisphere leadership."""

    def __init__(self, config: Dict[str, Any]) -> None:
        cross_cfg = get_cross_hemisphere_config(config)
        exploration_cfg = cross_cfg.get("exploration", {}) if cross_cfg else {}
        diversity_cfg = cross_cfg.get("diversity", {}) if cross_cfg else {}

        self.enabled = bool(exploration_cfg.get("enabled", False))
        self.mode = exploration_cfg.get("mode", "quota")

        self.window_size = int(exploration_cfg.get("window_size", 50))
        self.min_right_fraction = float(exploration_cfg.get("min_right_fraction", 0.25))

        self.interval_ticks = int(exploration_cfg.get("interval_ticks", 20))
        self.stuck_window = int(exploration_cfg.get("stuck_window", 6))

        self.allow_right_critic_on_high_risk = bool(
            exploration_cfg.get("allow_right_critic_on_high_risk", True)
        )
        self.exploration_safe_override = bool(
            exploration_cfg.get("exploration_safe_override", False)
        )

        self.convergence_warning_threshold = float(
            diversity_cfg.get("convergence_warning_threshold", 0.15)
        )

    def evaluate(
        self,
        tick_profile: Dict[str, Any],
        history: List[str],
        divergence: Optional[float] = None,
        tick_count: Optional[int] = None,
        task_risk: Optional[bool] = None,
    ) -> ExplorationDecision:
        if not self.enabled:
            return ExplorationDecision()

        high_risk = bool(task_risk)
        force_lead = False
        reason = ""

        if self.mode in ("hybrid", "stuck") and self._stuck_in_same_side(history):
            force_lead = True
            reason = "stuck_trigger"
        elif self.mode in ("hybrid", "drift") and divergence is not None:
            if divergence < self.convergence_warning_threshold:
                force_lead = True
                reason = "drift_trigger"
        elif self.mode in ("hybrid", "quota") and self._quota_violated(history):
            force_lead = True
            reason = "quota_trigger"
        elif self.mode == "interval" and self._interval_trigger(tick_count):
            force_lead = True
            reason = "interval_trigger"

        if not force_lead:
            return ExplorationDecision()

        if high_risk and not self.exploration_safe_override:
            if self.allow_right_critic_on_high_risk:
                return ExplorationDecision(force_right_critic=True, reason=reason)
            return ExplorationDecision()

        return ExplorationDecision(force_right_lead=True, reason=reason)

    def _quota_violated(self, history: List[str]) -> bool:
        window = history[-self.window_size:] if history else []
        if not window:
            return False
        right_fraction = window.count("right_lead") / max(1, len(window))
        return right_fraction < self.min_right_fraction

    def _interval_trigger(self, tick_count: Optional[int]) -> bool:
        if not tick_count or self.interval_ticks <= 0:
            return False
        return tick_count % self.interval_ticks == 0

    def _stuck_in_same_side(self, history: List[str]) -> bool:
        if self.stuck_window <= 0 or len(history) < self.stuck_window:
            return False
        window = history[-self.stuck_window:]
        return len(set(window)) == 1 and window[0] != "right_lead"
