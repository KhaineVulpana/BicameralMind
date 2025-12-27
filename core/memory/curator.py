"""Curator: Converts reflection insights into procedural bullets.

The Curator is responsible for:
1. Evaluating reflection insights
2. Converting insights into bullets
3. Deduplicating against existing knowledge
4. Managing bullet lifecycle (quarantine -> active -> shared)
5. Pruning low-quality bullets

CRITICAL: The Curator is the ONLY component that writes to procedural memory.
It evaluates insights from the Reflector and decides what to add.

Following ACE principles:
- Add bullets incrementally, never rewrite wholesale
- Start new bullets as QUARANTINED
- Promote based on outcome-based validation
- Prune based on persistent poor performance
"""

from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger

from .bullet import Bullet, BulletType, BulletStatus, Hemisphere
from .suggestion_store import Suggestion, SuggestionStore, _now_iso, _make_id
from .procedural_memory import ProceduralMemory
from .hemisphere_classifier import HemisphereClassifier
from .reflector import ReflectionInsight, InsightType


class Curator:
    """Manages the lifecycle of procedural memory bullets.

    The Curator sits between the Reflector and ProceduralMemory:

    Reflector -> Insights -> Curator -> Bullets -> ProceduralMemory

    It ensures quality control and prevents memory pollution.
    """

    def __init__(
        self,
        memory: ProceduralMemory,
        suggestion_store: Optional[SuggestionStore] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize curator.

        Args:
            memory: ProceduralMemory instance to manage
        """
        self.memory = memory
        self.suggestion_store = suggestion_store
        self.config = config or memory.get_cross_hemisphere_config()
        self.classifier = HemisphereClassifier(memory, use_llm_fallback=False)

    def _staging_config(self) -> Dict[str, Any]:
        return (self.memory.config.get("procedural_memory", {}) or {}).get("staging", {}) or {}

    async def curate(
        self,
        insights: List[ReflectionInsight],
        hemisphere: Hemisphere,
        auto_add: bool = True,
    ) -> List[Bullet]:
        """Curate insights into bullets.

        Args:
            insights: Insights from Reflector
            hemisphere: Which hemisphere these apply to
            auto_add: If True, automatically add bullets to memory

        Returns:
            List of bullets created (or that would be created)
        """
        if not insights:
            return []

        logger.debug(
            f" Curating {len(insights)} insights for {hemisphere.value}"
        )

        bullets_created = []

        for insight in insights:
            # Convert insight to bullet
            bullet = self._insight_to_bullet(insight, hemisphere)

            if not bullet:
                continue

            # Check for duplicates
            is_duplicate, existing_id = await self._check_duplicate(
                bullet,
                hemisphere,
            )

            if is_duplicate:
                logger.debug(
                    f"   Duplicate insight, skipping: {bullet.text[:60]}..."
                )
                # Instead of creating new, could increment existing
                # But for now, skip to avoid noise
                continue

            # Add to memory if auto_add
            if auto_add:
                staging_cfg = self._staging_config()
                staging_enabled = bool(staging_cfg.get("enabled", False))
                auto_assign = bool(staging_cfg.get("auto_assign", False))
                auto_threshold = float(staging_cfg.get("auto_assign_threshold", 0.85))
                review_threshold = float(staging_cfg.get("manual_review_threshold", 0.7))

                if staging_enabled:
                    staged = self.memory.stage_bullet(
                        text=bullet.text,
                        source_hemisphere=hemisphere,
                        bullet_type=bullet.type,
                        tags=bullet.tags,
                        confidence=bullet.confidence,
                        source_trace_id=bullet.source_trace_id,
                        metadata=bullet.metadata,
                        auto_assign=auto_assign,
                    )

                    if auto_assign:
                        result = await self.classifier.classify(
                            bullet_text=bullet.text,
                            bullet_type=bullet.type,
                            source_hint=hemisphere,
                            tags=bullet.tags,
                        )
                        if result.confidence >= auto_threshold and not result.ambiguous:
                            assigned = self.memory.assign_staged_bullet(
                                staged.id,
                                result.hemisphere,
                                reviewer="auto",
                            )
                            if assigned:
                                bullets_created.append(assigned)
                                logger.info(
                                    f"  OK Auto-assigned bullet: {assigned.id[:12]}... "
                                    f"to {assigned.side.value}"
                                )
                            else:
                                bullets_created.append(staged)
                        else:
                            priority = "high" if result.confidence < review_threshold else "medium"
                            self.memory.update_bullet_metadata(
                                staged.id,
                                {
                                    "classifier_suggestion": result.hemisphere.value,
                                    "classifier_confidence": result.confidence,
                                    "classifier_reasoning": result.reasoning,
                                    "review_priority": priority,
                                },
                            )
                            bullets_created.append(staged)
                    else:
                        bullets_created.append(staged)
                else:
                    created = self.memory.add(
                        text=bullet.text,
                        side=hemisphere,
                        bullet_type=bullet.type,
                        tags=bullet.tags,
                        confidence=bullet.confidence,
                        source_trace_id=bullet.source_trace_id,
                        status=BulletStatus.QUARANTINED,  # Always start quarantined
                    )
                    bullets_created.append(created)
                    logger.info(
                        f"  OK Created bullet: {created.id[:12]}... "
                        f"[{bullet.type.value}] {bullet.text[:60]}..."
                    )
            else:
                bullets_created.append(bullet)

        logger.info(
            f" Curated {len(bullets_created)} new bullets for {hemisphere.value}"
        )

        return bullets_created

    def _insight_to_bullet(
        self,
        insight: ReflectionInsight,
        hemisphere: Hemisphere,
    ) -> Optional[Bullet]:
        """Convert a reflection insight into a bullet.

        Args:
            insight: Insight from reflection
            hemisphere: Target hemisphere

        Returns:
            Bullet instance or None if insight is too low quality
        """
        # Filter out low-confidence insights
        if insight.confidence < 0.5:
            logger.debug(
                f"   Skipping low-confidence insight: {insight.confidence:.2f}"
            )
            return None

        # Filter out trivial insights
        if len(insight.text) < 10:
            logger.debug("   Skipping trivial insight (too short)")
            return None

        # Map InsightType to BulletType
        bullet_type_map = {
            InsightType.STRATEGY: BulletType.HEURISTIC,
            InsightType.PITFALL: BulletType.PITFALL,
            InsightType.PATTERN: BulletType.PATTERN,
            InsightType.TOOL_RULE: BulletType.TOOL_RULE,
            InsightType.HEURISTIC: BulletType.HEURISTIC,
            InsightType.EDGE_CASE: BulletType.PITFALL,
        }

        bullet_type = bullet_type_map.get(
            insight.insight_type,
            BulletType.HEURISTIC,
        )

        # Create bullet
        bullet = Bullet.create(
            text=insight.text,
            side=hemisphere,
            bullet_type=bullet_type,
            tags=insight.tags,
            confidence=insight.confidence,
            source_trace_id=insight.source_trace_id,
        )

        return bullet

    async def _check_duplicate(
        self,
        candidate: Bullet,
        hemisphere: Hemisphere,
    ) -> Tuple[bool, Optional[str]]:
        """Check if bullet is duplicate of existing knowledge.

        Args:
            candidate: Candidate bullet
            hemisphere: Hemisphere to check

        Returns:
            (is_duplicate, existing_bullet_id)
        """
        # Retrieve similar bullets
        similar_bullets, _ = self.memory.retrieve(
            query=candidate.text,
            side=hemisphere,
            k=5,
            include_shared=True,
        )

        # Check for high similarity
        for existing in similar_bullets:
            similarity = self._text_similarity(candidate.text, existing.text)

            if similarity > 0.9:  # Very high similarity threshold
                return (True, existing.id)

        return (False, None)

    def _text_similarity(self, text1: str, text2: str) -> float:
        """Simple text similarity metric.

        TODO: Could use embedding cosine similarity for better accuracy.
        For now, use simple character-based similarity.
        """
        # Simple character overlap ratio
        t1 = set(text1.lower().split())
        t2 = set(text2.lower().split())

        if not t1 or not t2:
            return 0.0

        intersection = len(t1 & t2)
        union = len(t1 | t2)

        return intersection / union if union > 0 else 0.0

    def _suggestion_config(self) -> Dict[str, Any]:
        cross_cfg = self.config or self.memory.get_cross_hemisphere_config()
        return cross_cfg.get("suggestions", {}) if cross_cfg else {}

    def _suggestions_enabled(self) -> bool:
        cross_cfg = self.config or self.memory.get_cross_hemisphere_config()
        if not cross_cfg or not cross_cfg.get("enabled", False):
            return False
        mode = cross_cfg.get("mode", "shared_only")
        if mode not in ("suggestions", "teaching"):
            return False
        return bool(self._suggestion_config().get("enabled", False))

    def _should_suggest(self, bullet: Bullet, config: Dict[str, Any]) -> bool:
        if bullet.status != BulletStatus.ACTIVE:
            return False
        if bullet.helpful_count < int(config.get("suggest_threshold", 2)):
            return False
        if bullet.harmful_count > int(config.get("harmful_tolerance", 0)):
            return False
        if bullet.confidence < float(config.get("min_suggest_confidence", 0.65)):
            return False
        return True

    def _has_equivalent_in_side(self, text: str, hemisphere: Hemisphere) -> bool:
        candidates, _ = self.memory.retrieve(
            query=text,
            side=hemisphere,
            k=5,
            include_shared=False,
        )
        for candidate in candidates:
            if self._text_similarity(candidate.text, text) > 0.9:
                return True
        return False

    def _already_in_shared(self, text: str) -> bool:
        candidates, _ = self.memory.retrieve(
            query=text,
            side=Hemisphere.LEFT,
            k=5,
            include_shared=True,
        )
        for candidate in candidates:
            if candidate.side == Hemisphere.SHARED and self._text_similarity(candidate.text, text) > 0.9:
                return True
        return False

    def generate_suggestions(
        self,
        bullets: List[Bullet],
        from_side: Hemisphere,
        to_side: Optional[Hemisphere] = None,
        reason: str = "suggested_from_outcome",
    ) -> List[Suggestion]:
        """Generate cross-hemisphere suggestions for eligible bullets."""
        if not self.suggestion_store or not self._suggestions_enabled():
            return []

        config = self._suggestion_config()
        max_pending = int(config.get("max_pending", 0))
        if max_pending and self.suggestion_store.count(status="pending") >= max_pending:
            return []
        target = to_side or (Hemisphere.RIGHT if from_side == Hemisphere.LEFT else Hemisphere.LEFT)
        suggestions: List[Suggestion] = []

        for bullet in bullets:
            if max_pending and self.suggestion_store.count(status="pending") >= max_pending:
                break
            if bullet.side == Hemisphere.SHARED:
                continue
            if not self._should_suggest(bullet, config):
                continue
            if self._already_in_shared(bullet.text):
                continue
            if self._has_equivalent_in_side(bullet.text, target):
                continue
            if self.suggestion_store.exists_active(bullet.id, target.value):
                continue

            suggestion = Suggestion(
                suggestion_id=_make_id("sg"),
                from_side=from_side.value,
                to_side=target.value,
                origin_bullet_id=bullet.id,
                suggested_text=bullet.text,
                tags=bullet.tags,
                reason=reason,
                status="pending",
                created_at=_now_iso(),
                delivered_at=None,
                resolved_at=None,
                trace_ids=[],
            )
            try:
                self.suggestion_store.create(suggestion)
                suggestions.append(suggestion)
            except ValueError:
                continue

        return suggestions

    async def prune_low_quality(
        self,
        hemisphere: Hemisphere,
        min_score: float = -0.5,
        min_age_days: int = 7,
        dry_run: bool = True,
    ) -> List[str]:
        """Prune bullets with persistently low scores.

        This is a maintenance operation run periodically.

        Args:
            hemisphere: Which hemisphere to prune
            min_score: Bullets below this score are candidates
            min_age_days: Only prune bullets older than this
            dry_run: If True, return what would be pruned without actually doing it

        Returns:
            List of bullet IDs that were (or would be) pruned
        """
        logger.info(
            f" Pruning {hemisphere.value} memory "
            f"(min_score={min_score}, min_age={min_age_days}d, dry_run={dry_run})"
        )

        if not self.memory or not getattr(self.memory, "enabled", False):
            return []

        try:
            min_age_days = max(0, int(min_age_days))
        except Exception:
            min_age_days = 7

        cutoff = datetime.now(timezone.utc) - timedelta(days=min_age_days)

        try:
            raw = self.memory.store.list_bullets(
                side=hemisphere.value,
                limit=10000,
                include_deprecated=True,
            )
        except Exception as exc:
            logger.warning(f"Prune list_bullets failed: {exc}")
            return []

        candidates: List[str] = []
        for pb in raw:
            bullet = self.memory._convert_bullet(pb)
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

            if score < float(min_score):
                candidates.append(bullet.id)

        if dry_run:
            return candidates

        pruned: List[str] = []
        for bid in candidates:
            if self.memory.store.set_status(bid, BulletStatus.DEPRECATED.value):
                pruned.append(bid)
        return pruned

    async def deduplicate(
        self,
        hemisphere: Hemisphere,
        similarity_threshold: float = 0.95,
        dry_run: bool = True,
    ) -> List[Tuple[str, str]]:
        """Deduplicate similar bullets.

        Args:
            hemisphere: Which hemisphere to deduplicate
            similarity_threshold: Similarity threshold for merging
            dry_run: If True, return what would be merged without doing it

        Returns:
            List of (kept_id, removed_id) tuples
        """
        logger.info(
            f" Deduplicating {hemisphere.value} memory "
            f"(threshold={similarity_threshold:.2f}, dry_run={dry_run})"
        )

        if not self.memory or not getattr(self.memory, "enabled", False):
            return []

        collection = f"procedural_{hemisphere.value}"

        # Prefer semantic dedup if deps are available
        try:
            from .deduplicator import Deduplicator
            from .bullet_merger import BulletMerger

            deduper = Deduplicator(self.memory.store, config={"dedup_threshold": float(similarity_threshold)})
            clusters = deduper.find_duplicates(collection_name=collection, threshold=float(similarity_threshold))
            if not clusters:
                return []

            pairs: List[Tuple[str, str]] = []
            for cluster in clusters:
                primary = getattr(cluster, "primary_bullet", None)
                if not primary:
                    continue
                for b in getattr(cluster, "bullets", []) or []:
                    if b.id != primary.id:
                        pairs.append((primary.id, b.id))

            if dry_run:
                return pairs

            merger = BulletMerger(self.memory.store)
            out: List[Tuple[str, str]] = []
            for cluster in clusters:
                res = merger.merge_cluster(cluster, collection_name=collection)
                for removed_id in res.archived_ids or []:
                    out.append((res.merged_bullet.id, removed_id))
            return out
        except Exception as exc:
            logger.warning(f"Semantic dedup unavailable, using exact-text dedup ({exc})")

        try:
            raw = self.memory.store.list_bullets(side=hemisphere.value, limit=10000, include_deprecated=True)
        except Exception as exc:
            logger.warning(f"Dedup list_bullets failed: {exc}")
            return []

        bullets = [self.memory._convert_bullet(pb) for pb in raw]
        by_text: Dict[str, List[Bullet]] = {}
        for b in bullets:
            norm = " ".join((b.text or "").strip().lower().split())
            if not norm:
                continue
            by_text.setdefault(norm, []).append(b)

        pairs: List[Tuple[str, str]] = []
        for _, group in by_text.items():
            if len(group) < 2:
                continue
            group.sort(key=lambda b: float(b.score()), reverse=True)
            keep = group[0]
            for dup in group[1:]:
                pairs.append((keep.id, dup.id))

        if dry_run:
            return pairs

        out: List[Tuple[str, str]] = []
        for keep_id, dup_id in pairs:
            if self.memory.store.set_status(dup_id, BulletStatus.DEPRECATED.value):
                out.append((keep_id, dup_id))
        return out

    async def promote_successful_bullets(
        self,
        hemisphere: Hemisphere,
        promote_threshold: int = 3,
    ) -> List[str]:
        """Manually trigger promotion check for bullets.

        This is usually handled automatically by ProceduralMemory,
        but can be explicitly triggered.

        Args:
            hemisphere: Which hemisphere to check
            promote_threshold: Helpful count needed for promotion

        Returns:
            List of bullet IDs that were promoted
        """
        logger.info(
            f"  Checking for promotable bullets in {hemisphere.value} "
            f"(threshold={promote_threshold})"
        )

        promoted_ids = []

        # Retrieve all active bullets
        all_bullets, _ = self.memory.retrieve(
            query="",  # Empty query to get all
            side=hemisphere,
            k=1000,  # Get many
            min_confidence=0.0,
            include_shared=False,
        )

        for bullet in all_bullets:
            if bullet.should_promote_to_shared(threshold=promote_threshold):
                # Promotion is handled automatically by store
                # But we can record which ones are eligible
                promoted_ids.append(bullet.id)
                logger.info(
                    f"    Eligible for promotion: {bullet.id[:12]}... "
                    f"(+{bullet.helpful_count}/-{bullet.harmful_count})"
                )

        logger.info(f"Found {len(promoted_ids)} bullets eligible for promotion")

        return promoted_ids

    async def activate_quarantined_bullets(
        self,
        hemisphere: Hemisphere,
        activation_threshold: int = 2,
    ) -> List[str]:
        """Check quarantined bullets for activation.

        Args:
            hemisphere: Which hemisphere to check
            activation_threshold: Helpful count needed for activation

        Returns:
            List of bullet IDs that were activated
        """
        logger.info(
            f" Checking quarantined bullets in {hemisphere.value} "
            f"(threshold={activation_threshold})"
        )

        activated_ids = []

        # Note: This is usually handled automatically by the store
        # But we can explicitly check and report

        # Retrieve quarantined bullets
        # TODO: Need ability to filter by status in retrieve

        logger.info(f"Activated {len(activated_ids)} quarantined bullets")

        return activated_ids

    def get_curation_stats(self, hemisphere: Hemisphere) -> Dict[str, Any]:
        """Get statistics about curated memory.

        Args:
            hemisphere: Which hemisphere to analyze

        Returns:
            Dictionary of statistics
        """
        stats = self.memory.get_stats()

        # TODO: Add more detailed stats:
        # - Bullets by type
        # - Bullets by status
        # - Average scores
        # - Promotion rate
        # - Deprecation rate

        return {
            "hemisphere": hemisphere.value,
            "total_bullets": stats.get("collections", {}).get(hemisphere.value, {}).get("count", 0),
            "enabled": stats.get("enabled", False),
        }
