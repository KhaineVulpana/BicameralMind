"""Explicit teaching API for cross-hemisphere transfer."""

from typing import Any, Dict, List, Optional
import re

from .procedural_memory import ProceduralMemory
from .suggestion_store import Suggestion, SuggestionStore, _now_iso, _make_id


def _neutralize(text: str) -> str:
    rules = [
        (r"\bmust not\b", "avoid"),
        (r"\bdo not\b", "avoid"),
        (r"\bnever\b", "avoid"),
        (r"\bmust\b", "should"),
        (r"\balways\b", "usually"),
        (r"\brequired\b", "recommended"),
    ]
    updated = text
    for pattern, replacement in rules:
        updated = re.sub(pattern, replacement, updated, flags=re.IGNORECASE)
    return updated


class TeachingAPI:
    """Create teaching suggestions across hemispheres."""

    def __init__(
        self,
        memory: ProceduralMemory,
        suggestion_store: SuggestionStore,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.memory = memory
        self.suggestion_store = suggestion_store
        self.config = config or memory.get_cross_hemisphere_config()

    def teach_bullet(
        self,
        from_side: str,
        to_side: str,
        bullet_id: str,
        translate: bool = False,
        reason: str = "teaching",
    ) -> str:
        bullets = self.memory.get_bullets_by_ids([bullet_id])
        if not bullets:
            raise ValueError(f"Bullet not found: {bullet_id}")
        bullet = bullets[0]
        suggested_text = _neutralize(bullet.text) if translate else bullet.text
        suggestion = Suggestion(
            suggestion_id=_make_id("sg"),
            from_side=from_side,
            to_side=to_side,
            origin_bullet_id=bullet_id,
            suggested_text=suggested_text,
            tags=bullet.tags,
            reason=reason,
            status="pending",
            created_at=_now_iso(),
            delivered_at=None,
            resolved_at=None,
            trace_ids=[],
        )
        return self.suggestion_store.create(suggestion)

    def teach_text(
        self,
        from_side: str,
        to_side: str,
        text: str,
        tags: Optional[List[str]] = None,
        translate: bool = False,
        reason: str = "teaching",
    ) -> str:
        suggested_text = _neutralize(text) if translate else text
        suggestion = Suggestion(
            suggestion_id=_make_id("sg"),
            from_side=from_side,
            to_side=to_side,
            origin_bullet_id="",
            suggested_text=suggested_text,
            tags=tags or [],
            reason=reason,
            status="pending",
            created_at=_now_iso(),
            delivered_at=None,
            resolved_at=None,
            trace_ids=[],
        )
        return self.suggestion_store.create(suggestion)
