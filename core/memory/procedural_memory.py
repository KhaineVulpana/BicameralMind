"""High-level ProceduralMemory API for Bicameral Mind.

This wraps the lower-level ProceduralMemoryStore and provides:
- Modern Bullet dataclass API
- Simplified CRUD operations
- Automatic scoring and promotion logic
- Integration with consciousness ticks (gating, not scoring)
"""

from typing import Dict, List, Optional, Tuple, Any
from loguru import logger

from .bullet import Bullet, BulletType, BulletStatus, Hemisphere
from .procedural_store import ProceduralMemoryStore, ProceduralBullet


class ProceduralMemory:
    """High-level API for procedural memory management.

    Design principles:
    - Each hemisphere queries its own collection + shared
    - Bullets are added incrementally, never rewritten wholesale
    - Scoring is outcome-based (NOT tick-based)
    - Ticks gate reflection depth, not learning
    - Promotion to shared requires repeated success
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize procedural memory system."""
        self.store = ProceduralMemoryStore(config)
        self.enabled = self.store.enabled

        # Track which bullets were used in current context
        self._active_bullet_ids: Dict[str, List[str]] = {
            "left": [],
            "right": [],
            "shared": [],
        }

    def add(
        self,
        text: str,
        side: Hemisphere,
        bullet_type: BulletType = BulletType.HEURISTIC,
        tags: Optional[List[str]] = None,
        confidence: float = 0.5,
        source_trace_id: str = "",
        status: BulletStatus = BulletStatus.QUARANTINED,
    ) -> Bullet:
        """Add a new procedural bullet.

        New bullets start as QUARANTINED by default and require
        validation before being promoted to ACTIVE.
        """
        if not self.enabled:
            raise RuntimeError("ProceduralMemory is disabled")

        # Create modern Bullet
        bullet = Bullet.create(
            text=text,
            side=side,
            bullet_type=bullet_type,
            tags=tags,
            confidence=confidence,
            source_trace_id=source_trace_id,
        )
        bullet.status = status

        # Store in vector DB
        self.store.add_bullet(
            side=side.value,
            text=bullet.text,
            bullet_type=bullet_type.value,
            tags=tags,
            status=status.value,
            confidence=confidence,
            source_trace_id=source_trace_id,
            bullet_id=bullet.id,
        )

        logger.debug(f"📝 Added bullet: {bullet.id[:16]}... to {side.value}")
        return bullet

    def retrieve(
        self,
        query: str,
        side: Hemisphere,
        tags: Optional[List[str]] = None,
        k: Optional[int] = None,
        min_confidence: Optional[float] = None,
        include_shared: bool = True,
    ) -> Tuple[List[Bullet], List[str]]:
        """Retrieve relevant bullets for a query.

        Returns:
            (bullets, used_ids) - bullets are modern Bullet objects,
                                  used_ids are for tracking outcomes
        """
        if not self.enabled:
            return ([], [])

        # Query the store
        old_bullets, used_ids = self.store.query(
            side=side.value,
            query_text=query,
            tags=tags,
            k=k,
            min_confidence=min_confidence,
            include_shared=include_shared,
        )

        # Convert ProceduralBullet -> Bullet
        bullets = [self._convert_bullet(b) for b in old_bullets]

        # Track active bullets for this hemisphere
        self._active_bullet_ids[side.value] = used_ids

        logger.debug(
            f"🔍 Retrieved {len(bullets)} bullets for {side.value} "
            f"(shared={include_shared})"
        )

        return bullets, used_ids

    def record_outcome(
        self,
        bullet_ids: List[str],
        helpful: bool,
        side: Optional[Hemisphere] = None,
    ) -> None:
        """Record outcome-based feedback for bullets.

        CRITICAL: This is the ONLY way helpful/harmful counters are incremented.
        NOT from ticks, but from actual outcomes:
        - Tool success/failure
        - Test pass/fail
        - User confirmation/correction
        - Validator results

        Args:
            bullet_ids: IDs of bullets that were used
            helpful: True if outcome was positive, False if negative
            side: Optional hemisphere context (for logging)
        """
        if not self.enabled or not bullet_ids:
            return

        self.store.record_outcome(bullet_ids, helpful=helpful)

        action = "✅ helpful" if helpful else "❌ harmful"
        side_str = f" ({side.value})" if side else ""
        logger.info(
            f"📊 Recorded {action} for {len(bullet_ids)} bullets{side_str}"
        )

    def clear_active_bullets(self, side: Hemisphere) -> None:
        """Clear the tracked active bullets for a hemisphere."""
        self._active_bullet_ids[side.value] = []

    def get_active_bullets(self, side: Hemisphere) -> List[str]:
        """Get currently active bullet IDs for a hemisphere."""
        return self._active_bullet_ids.get(side.value, [])

    def _convert_bullet(self, old_bullet: ProceduralBullet) -> Bullet:
        """Convert legacy ProceduralBullet to modern Bullet."""
        return Bullet.from_dict(
            {
                "id": old_bullet.id,
                "text": old_bullet.text,
                "side": old_bullet.side,
                "type": old_bullet.type,
                "tags": old_bullet.tags,
                "status": old_bullet.status,
                "confidence": old_bullet.confidence,
                "helpful_count": old_bullet.helpful_count,
                "harmful_count": old_bullet.harmful_count,
                "created_at": old_bullet.created_at,
                "last_used_at": old_bullet.last_used_at,
                "source_trace_id": old_bullet.source_trace_id,
            }
        )

    def format_bullets_for_prompt(
        self,
        bullets: List[Bullet],
        max_bullets: Optional[int] = None,
    ) -> str:
        """Format bullets as a playbook string for LLM context.

        Following ACE principles:
        - Structured sections by type
        - Include metadata (IDs, scores)
        - Preserve detail (no summarization)
        """
        if not bullets:
            return ""

        # Group by type
        by_type: Dict[BulletType, List[Bullet]] = {}
        for bullet in bullets[:max_bullets] if max_bullets else bullets:
            if bullet.type not in by_type:
                by_type[bullet.type] = []
            by_type[bullet.type].append(bullet)

        sections = []

        # Format each type as a section
        type_names = {
            BulletType.TOOL_RULE: "TOOL USAGE RULES",
            BulletType.HEURISTIC: "STRATEGIES AND HEURISTICS",
            BulletType.CHECKLIST: "CHECKLISTS",
            BulletType.PITFALL: "COMMON MISTAKES TO AVOID",
            BulletType.TEMPLATE: "USEFUL CODE SNIPPETS AND TEMPLATES",
            BulletType.EXAMPLE: "CONCRETE EXAMPLES",
            BulletType.PATTERN: "RECOGNIZED PATTERNS",
            BulletType.CONCEPT: "DOMAIN CONCEPTS",
        }

        for bullet_type, type_bullets in sorted(by_type.items(), key=lambda x: x[0].value):
            section_name = type_names.get(bullet_type, bullet_type.value.upper())
            lines = [f"\n## {section_name}\n"]

            # Sort by score
            type_bullets.sort(key=lambda b: b.score(), reverse=True)

            for bullet in type_bullets:
                tags_str = f" [{', '.join(bullet.tags)}]" if bullet.tags else ""
                score = bullet.score()
                lines.append(
                    f"[{bullet.id[:12]}]{tags_str} {bullet.text} "
                    f"(score: {score:.2f})"
                )

            sections.append("\n".join(lines))

        return "\n".join(sections)

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        if not self.enabled:
            return {"enabled": False}

        stats = {
            "enabled": True,
            "collections": {},
        }

        for side in ["left", "right", "shared"]:
            try:
                col = self.store._collections[side]
                count = col.count()
                stats["collections"][side] = {"count": count}
            except Exception as e:
                logger.warning(f"Failed to get stats for {side}: {e}")
                stats["collections"][side] = {"count": 0, "error": str(e)}

        return stats

    def prune_low_quality(
        self,
        side: Hemisphere,
        min_score: float = -0.5,
        min_age_days: int = 7,
    ) -> int:
        """Prune bullets with persistently low scores.

        This is a maintenance operation, not a core learning mechanism.
        Should be run periodically (e.g., nightly).

        Args:
            side: Which hemisphere to prune
            min_score: Bullets below this score are candidates
            min_age_days: Only prune bullets older than this

        Returns:
            Number of bullets pruned
        """
        # TODO: Implement pruning logic
        # For now, just return 0
        logger.warning("Pruning not yet implemented")
        return 0

    def deduplicate(
        self,
        side: Hemisphere,
        similarity_threshold: float = 0.95,
    ) -> int:
        """Remove near-duplicate bullets.

        Uses semantic similarity of embeddings to identify duplicates,
        keeping the one with higher score.

        Args:
            side: Which hemisphere to deduplicate
            similarity_threshold: Cosine similarity threshold

        Returns:
            Number of bullets removed
        """
        # TODO: Implement deduplication logic
        # For now, just return 0
        logger.warning("Deduplication not yet implemented")
        return 0
