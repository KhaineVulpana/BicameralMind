"""High-level ProceduralMemory API for Bicameral Mind.

This wraps the lower-level ProceduralMemoryStore and provides:
- Modern Bullet dataclass API
- Simplified CRUD operations
- Automatic scoring and promotion logic
- Integration with consciousness ticks (gating, not scoring)
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any
from loguru import logger

from .bullet import Bullet, BulletType, BulletStatus, Hemisphere
from .config_utils import get_cross_hemisphere_config
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
        self.config = config or {}
        self.store = ProceduralMemoryStore(config)
        self.enabled = self.store.enabled

        # Track which bullets were used in current context
        self._active_bullet_ids: Dict[str, List[str]] = {
            "left": [],
            "right": [],
            "shared": [],
        }

    def _get_staging_config(self) -> Dict[str, Any]:
        return (self.config.get("procedural_memory", {}) or {}).get("staging", {}) or {}

    def add(
        self,
        text: str,
        side: Hemisphere,
        bullet_type: BulletType = BulletType.HEURISTIC,
        tags: Optional[List[str]] = None,
        confidence: float = 0.5,
        source_trace_id: str = "",
        status: BulletStatus = BulletStatus.QUARANTINED,
        metadata: Optional[Dict[str, Any]] = None,
        stage: Optional[bool] = None,
        auto_assign: Optional[bool] = None,
        source_hemisphere: Optional[Hemisphere] = None,
    ) -> Bullet:
        'Add a new procedural bullet.'

        # When staging is enabled, new bullets are staged before assignment.
        if not self.enabled:
            raise RuntimeError('ProceduralMemory is disabled')

        staging_cfg = self._get_staging_config()
        stage_enabled = bool(staging_cfg.get('enabled', False))
        use_stage = stage_enabled if stage is None else stage

        if use_stage:
            return self.stage_bullet(
                text=text,
                source_hemisphere=source_hemisphere or side,
                bullet_type=bullet_type,
                tags=tags,
                confidence=confidence,
                source_trace_id=source_trace_id,
                metadata=metadata,
                auto_assign=auto_assign,
            )

        bullet = Bullet.create(
            text=text,
            side=side,
            bullet_type=bullet_type,
            tags=tags,
            confidence=confidence,
            source_trace_id=source_trace_id,
        )
        if metadata:
            bullet.metadata = metadata
        bullet.status = status

        self.store.add_bullet(
            side=side.value,
            text=bullet.text,
            bullet_type=bullet_type.value,
            tags=tags,
            status=status.value,
            confidence=confidence,
            source_trace_id=source_trace_id,
            metadata=metadata,
            bullet_id=bullet.id,
        )

        logger.debug(f'Added bullet: {bullet.id[:16]}... to {side.value}')
        return bullet

    def stage_bullet(
        self,
        text: str,
        source_hemisphere: Hemisphere,
        bullet_type: BulletType = BulletType.HEURISTIC,
        tags: Optional[List[str]] = None,
        confidence: float = 0.5,
        source_trace_id: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        auto_assign: Optional[bool] = None,
    ) -> Bullet:
        'Add a bullet to staging (awaiting hemisphere assignment).'
        if not self.enabled:
            raise RuntimeError('ProceduralMemory is disabled')

        staging_cfg = self._get_staging_config()
        auto_assign = auto_assign if auto_assign is not None else bool(
            staging_cfg.get('auto_assign', False)
        )

        meta = dict(metadata or {})
        meta['source_hemisphere'] = source_hemisphere.value

        if auto_assign:
            meta["auto_assign_requested"] = True

        bullet = Bullet.create(
            text=text,
            side=Hemisphere.STAGING,
            bullet_type=bullet_type,
            tags=tags,
            confidence=confidence,
            source_trace_id=source_trace_id,
        )
        bullet.status = BulletStatus.STAGED
        bullet.metadata = meta

        self.store.add_bullet(
            side=Hemisphere.STAGING.value,
            text=bullet.text,
            bullet_type=bullet_type.value,
            tags=tags,
            status=BulletStatus.STAGED.value,
            confidence=confidence,
            source_trace_id=source_trace_id,
            metadata=meta,
            bullet_id=bullet.id,
        )

        logger.debug(f'Staged bullet: {bullet.id[:16]}...')
        return bullet

    def assign_staged_bullet(
        self,
        bullet_id: str,
        target_hemisphere: Hemisphere,
        reviewer: str = 'manual',
    ) -> Optional[Bullet]:
        'Assign a staged bullet to a hemisphere (quarantined).'
        staged = self.store.get_bullet(Hemisphere.STAGING.value, bullet_id)
        if not staged:
            return None

        metadata = dict(staged.metadata or {})
        metadata.update(
            {
                'assigned_by': reviewer,
                'assigned_at': staged.created_at,
                'original_staging_id': bullet_id,
            }
        )

        self.store.delete_bullet(Hemisphere.STAGING.value, bullet_id)

        created = self.add(
            text=staged.text,
            side=target_hemisphere,
            bullet_type=BulletType(staged.type),
            tags=staged.tags,
            confidence=staged.confidence,
            source_trace_id=staged.source_trace_id,
            status=BulletStatus.QUARANTINED,
            metadata=metadata,
            stage=False,
        )
        return created

    def list_staged(self, limit: int = 100, include_deprecated: bool = False) -> List[Bullet]:
        'List staged bullets awaiting assignment.'
        staged = self.store.list_bullets(
            Hemisphere.STAGING.value,
            limit=limit,
            include_deprecated=include_deprecated,
        )
        return [self._convert_bullet(b) for b in staged]

    def reject_staged_bullet(self, bullet_id: str, reason: str = '', reviewer: str = 'manual') -> bool:
        'Reject and delete a staged bullet.'
        try:
            self.store.delete_bullet(Hemisphere.STAGING.value, bullet_id)
        except Exception:
            return False
        logger.info(f'Rejected staged bullet {bullet_id[:12]} (reviewer={reviewer}, reason={reason})')
        return True

    def retrieve(
        self,
        query: str,
        side: Hemisphere,
        tags: Optional[List[str]] = None,
        statuses: Optional[List[str]] = None,
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

        old_bullets, used_ids = self.store.query(
            side=side.value,
            query_text=query,
            tags=tags,
            statuses=statuses,
            k=k,
            min_confidence=min_confidence,
            include_shared=include_shared,
        )

        bullets = [self._convert_bullet(b) for b in old_bullets]

        self._active_bullet_ids[side.value] = used_ids

        logger.debug(
            f"Retrieved {len(bullets)} bullets for {side.value} (shared={include_shared})"
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
        """
        if not self.enabled or not bullet_ids:
            return

        self.store.record_outcome(bullet_ids, helpful=helpful)

        action = "helpful" if helpful else "harmful"
        side_str = f" ({side.value})" if side else ""
        logger.info(
            f"Recorded {action} for {len(bullet_ids)} bullets{side_str}"
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
                "metadata": old_bullet.metadata or {},
            }
        )

    def get_cross_hemisphere_config(self) -> Dict[str, Any]:
        """Return merged cross-hemisphere config."""
        return get_cross_hemisphere_config(self.config)

    def get_bullets_by_ids(self, bullet_ids: List[str]) -> List[Bullet]:
        """Fetch bullets by ids across collections."""
        if not self.enabled or not bullet_ids:
            return []
        bullets = self.store.get_bullets_by_ids(bullet_ids)
        return [self._convert_bullet(b) for b in bullets]

    def list_bullets(
        self,
        side: Hemisphere,
        *,
        limit: int = 1000,
        statuses: Optional[List[str]] = None,
        include_deprecated: bool = False,
    ) -> List[Bullet]:
        """List bullets for a hemisphere (non-semantic)."""
        if not self.enabled:
            return []
        raw = self.store.list_bullets(side.value, limit=limit, include_deprecated=include_deprecated)
        bullets = [self._convert_bullet(b) for b in raw]
        if statuses:
            allowed = {str(s).lower().strip() for s in statuses if s and str(s).strip()}
            bullets = [b for b in bullets if str(getattr(b.status, "value", b.status)).lower() in allowed]
        return bullets

    def update_bullet_metadata(self, bullet_id: str, updates: Dict[str, Any]) -> bool:
        """Update metadata for a stored bullet."""
        if not self.enabled:
            return False
        return self.store.update_metadata(bullet_id, updates)

    def set_bullet_status(self, bullet_id: str, status: BulletStatus) -> bool:
        """Update status for a stored bullet."""
        if not self.enabled:
            return False
        return self.store.set_status(bullet_id, status.value)

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

        by_type: Dict[BulletType, List[Bullet]] = {}
        for bullet in bullets[:max_bullets] if max_bullets else bullets:
            if bullet.type not in by_type:
                by_type[bullet.type] = []
            by_type[bullet.type].append(bullet)

        sections = []

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

        for side in ["left", "right", "shared", "staging"]:
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
        """Prune bullets with persistently low scores."""
        if not self.enabled:
            return 0

        try:
            min_age_days = max(0, int(min_age_days))
        except Exception:
            min_age_days = 7

        cutoff = datetime.now(timezone.utc) - timedelta(days=min_age_days)

        try:
            raw = self.store.list_bullets(side=side.value, limit=10000, include_deprecated=True)
        except Exception as exc:
            logger.warning(f"Prune list_bullets failed: {exc}")
            return 0

        pruned = 0
        for pb in raw:
            bullet = self._convert_bullet(pb)
            if str(getattr(bullet.status, "value", bullet.status)) == BulletStatus.DEPRECATED.value:
                continue

            created_at = bullet.created_at
            if isinstance(created_at, datetime):
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
                else:
                    created_at = created_at.astimezone(timezone.utc)
            else:
                created_at = datetime.now(timezone.utc)

            if created_at > cutoff:
                continue

            try:
                score = float(bullet.score())
            except Exception:
                score = 0.0

            if score >= float(min_score):
                continue

            if self.store.set_status(bullet.id, BulletStatus.DEPRECATED.value):
                pruned += 1

        if pruned:
            logger.info(f"Pruned {pruned} bullets from {side.value} (deprecated)")
        return pruned

    def deduplicate(
        self,
        side: Hemisphere,
        similarity_threshold: float = 0.95,
    ) -> int:
        """Remove near-duplicate bullets."""
        if not self.enabled:
            return 0

        collection = f"procedural_{side.value}"

        # Prefer semantic dedup if dependencies are available; otherwise fallback to exact-text dedup.
        try:
            from .deduplicator import Deduplicator
            from .bullet_merger import BulletMerger

            deduper = Deduplicator(self.store, config={"dedup_threshold": float(similarity_threshold)})
            clusters = deduper.find_duplicates(collection_name=collection, threshold=float(similarity_threshold))
            if not clusters:
                return 0

            merger = BulletMerger(self.store)
            merged_count = 0
            for cluster in clusters:
                res = merger.merge_cluster(cluster, collection_name=collection)
                merged_count += len(res.archived_ids or [])
            return merged_count
        except Exception as exc:
            logger.warning(f"Semantic dedup unavailable, using exact-text dedup ({exc})")

        try:
            raw = self.store.list_bullets(side=side.value, limit=10000, include_deprecated=True)
        except Exception as exc:
            logger.warning(f"Dedup list_bullets failed: {exc}")
            return 0

        bullets = [self._convert_bullet(pb) for pb in raw]
        by_text: Dict[str, List[Bullet]] = {}
        for b in bullets:
            norm = " ".join((b.text or "").strip().lower().split())
            if not norm:
                continue
            by_text.setdefault(norm, []).append(b)

        removed = 0
        for norm, group in by_text.items():
            if len(group) < 2:
                continue
            group.sort(key=lambda b: float(b.score()), reverse=True)
            keep = group[0]
            for dup in group[1:]:
                if str(getattr(dup.status, "value", dup.status)) == BulletStatus.DEPRECATED.value:
                    continue
                if self.store.set_status(dup.id, BulletStatus.DEPRECATED.value):
                    removed += 1
        return removed
