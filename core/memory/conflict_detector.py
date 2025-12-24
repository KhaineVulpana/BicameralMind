"""Conflict detection for cross-hemisphere teaching."""

from typing import Any, Dict, Iterable, List, Optional

from .bullet import Bullet
from .config_utils import get_cross_hemisphere_config


POLARITY_NEG = {"never", "do not", "avoid", "must not"}
POLARITY_POS = {"must", "always", "required"}


class ConflictDetector:
    """Detect contradictory bullets."""

    def __init__(self, config: Optional[Dict[str, Any]] = None, similarity_threshold: float = 0.88) -> None:
        cross_cfg = get_cross_hemisphere_config(config or {})
        conflicts_cfg = cross_cfg.get("conflicts", {}) if cross_cfg else {}
        self.enabled = bool(conflicts_cfg.get("enabled", True))
        self.policy = conflicts_cfg.get("policy", "quarantine_and_flag")
        self.similarity_threshold = similarity_threshold

    def detect_conflict(self, a: Bullet, b: Bullet, similarity: float) -> bool:
        if similarity < self.similarity_threshold:
            return False
        a_text = a.text.lower()
        b_text = b.text.lower()
        a_neg = any(word in a_text for word in POLARITY_NEG)
        b_neg = any(word in b_text for word in POLARITY_NEG)
        a_pos = any(word in a_text for word in POLARITY_POS)
        b_pos = any(word in b_text for word in POLARITY_POS)
        return (a_neg and b_pos) or (a_pos and b_neg)

    def find_conflicts(self, incoming_bullet: Bullet, existing_bullets: Iterable[Bullet]) -> List[Bullet]:
        if not self.enabled:
            return []
        conflicts: List[Bullet] = []
        for existing in existing_bullets:
            sim = self._text_similarity(incoming_bullet.text, existing.text)
            if self.detect_conflict(incoming_bullet, existing, sim):
                conflicts.append(existing)
        return conflicts

    @staticmethod
    def _text_similarity(text1: str, text2: str) -> float:
        t1 = set(text1.lower().split())
        t2 = set(text2.lower().split())
        if not t1 or not t2:
            return 0.0
        intersection = len(t1 & t2)
        union = len(t1 | t2)
        return intersection / union if union > 0 else 0.0
