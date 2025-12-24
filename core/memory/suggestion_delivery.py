"""Suggestion delivery pipeline for cross-hemisphere learning."""

from typing import Any, Dict, List, Optional

from .bullet import BulletStatus, Hemisphere
from .config_utils import get_cross_hemisphere_config
from .conflict_detector import ConflictDetector
from .diversity_metrics import DiversityMetrics
from .procedural_memory import ProceduralMemory
from .suggestion_store import SuggestionStore, Suggestion


def can_deliver_suggestions(tick_profile: Dict[str, Any], config: Dict[str, Any]) -> bool:
    if not config or not config.get("enabled", False):
        return False
    suggestions_cfg = config.get("suggestions", {}) or {}
    if not suggestions_cfg.get("enabled", False):
        return False
    if suggestions_cfg.get("deliver_when_idle", True) and not tick_profile.get("is_idle", False):
        return False
    pressure = float(tick_profile.get("pressure", 0.0))
    if pressure > float(suggestions_cfg.get("max_pressure_to_deliver", 0.35)):
        return False
    return True


class SuggestionDelivery:
    """Deliver pending suggestions into the receiving hemisphere."""

    def __init__(
        self,
        memory: ProceduralMemory,
        suggestion_store: SuggestionStore,
        config: Optional[Dict[str, Any]] = None,
        conflict_detector: Optional[ConflictDetector] = None,
    ) -> None:
        self.memory = memory
        self.suggestion_store = suggestion_store
        self.config = config or get_cross_hemisphere_config(memory.config)
        self.conflict_detector = conflict_detector or ConflictDetector(memory.config)
        self.diversity_metrics = DiversityMetrics(memory, memory.config)

    def deliver_pending(
        self,
        tick_profile: Dict[str, Any],
        to_side: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Suggestion]:
        if not can_deliver_suggestions(tick_profile, self.config):
            return []

        diversity_cfg = (self.config or {}).get("diversity", {}) or {}
        if diversity_cfg.get("enabled") and diversity_cfg.get("throttle_on_convergence"):
            metrics = self.diversity_metrics.compute_from_memory()
            if metrics.get("converged"):
                return []

        suggestions_cfg = (self.config or {}).get("suggestions", {}) or {}
        limit = limit or int(suggestions_cfg.get("deliver_budget_per_tick", 1))
        expiry_days = int(suggestions_cfg.get("expiry_days", 0))
        if expiry_days > 0:
            self.suggestion_store.expire_old(expiry_days)

        delivered: List[Suggestion] = []
        for suggestion in self.suggestion_store.list_pending(to_side=to_side)[:limit]:
            if suggestion.from_side == suggestion.to_side:
                self.suggestion_store.resolve(
                    suggestion.suggestion_id,
                    accepted=False,
                    reason="invalid_target",
                )
                continue
            if self._has_equivalent_in_target(suggestion):
                self.suggestion_store.resolve(
                    suggestion.suggestion_id,
                    accepted=False,
                    reason="duplicate_in_target",
                )
                continue

            bullet = self._apply_suggestion(suggestion)
            self.suggestion_store.mark_delivered(
                suggestion.suggestion_id,
                delivered_bullet_id=bullet.id,
            )
            delivered.append(suggestion)

        return delivered

    def _apply_suggestion(self, suggestion: Suggestion):
        to_side = Hemisphere(suggestion.to_side)
        new_bullet = self.memory.add(
            text=suggestion.suggested_text,
            side=to_side,
            tags=suggestion.tags,
            status=BulletStatus.QUARANTINED,
            confidence=0.5,
            metadata={
                "suggestion_id": suggestion.suggestion_id,
                "origin_bullet_id": suggestion.origin_bullet_id,
                "taught_from": suggestion.from_side,
            },
        )

        if self.conflict_detector.enabled:
            existing, _ = self.memory.retrieve(
                query=suggestion.suggested_text,
                side=to_side,
                k=20,
                include_shared=False,
            )
            conflicts = self.conflict_detector.find_conflicts(new_bullet, existing)
            if conflicts:
                conflict_ids = [c.id for c in conflicts]
                self.memory.update_bullet_metadata(new_bullet.id, {"conflicts_with": conflict_ids})

        return new_bullet

    def _has_equivalent_in_target(self, suggestion: Suggestion) -> bool:
        to_side = Hemisphere(suggestion.to_side)
        candidates, _ = self.memory.retrieve(
            query=suggestion.suggested_text,
            side=to_side,
            k=5,
            include_shared=False,
        )
        for candidate in candidates:
            if self._text_similarity(candidate.text, suggestion.suggested_text) >= 0.9:
                return True
        return False

    @staticmethod
    def _text_similarity(text1: str, text2: str) -> float:
        t1 = set(text1.lower().split())
        t2 = set(text2.lower().split())
        if not t1 or not t2:
            return 0.0
        intersection = len(t1 & t2)
        union = len(t1 | t2)
        return intersection / union if union else 0.0
