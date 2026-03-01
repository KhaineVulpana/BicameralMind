"""Bullet Merger - Consolidates duplicate bullets"""
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json

from .bullet import Bullet
from .procedural_store import ProceduralMemoryStore
from .deduplicator import DuplicateCluster

logger = logging.getLogger(__name__)


@dataclass
class MergeResult:
    """Result from bullet merge operation"""
    merged_bullet: Bullet
    source_bullets: List[Bullet]
    merge_timestamp: datetime = field(default_factory=datetime.now)
    archived_ids: List[str] = field(default_factory=list)


@dataclass
class MergeHistory:
    """History entry for merged bullets"""
    merge_id: str
    timestamp: datetime
    primary_bullet_id: str
    merged_bullet_ids: List[str]
    reason: str = "deduplication"


class BulletMerger:
    """
    Bullet Merger System

    Consolidates duplicate bullets while preserving:
    - Highest quality content
    - Combined scores and metadata
    - Audit trail of merges
    """

    def __init__(
        self,
        store: ProceduralMemoryStore,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize bullet merger

        Args:
            store: ProceduralStore instance
            config: Configuration dict
        """
        self.store = store
        self.config = config or {}

        # Merge settings
        self.archive_merged = self.config.get("archive_merged_bullets", True)
        self.archive_path = self.config.get("archive_path", "./data/memory/archive")

        # Merge history
        self.merge_history: List[MergeHistory] = []

        # Statistics
        self.stats = {
            "total_merges": 0,
            "total_bullets_merged": 0,
        }

        logger.info("BulletMerger initialized")

    def merge_cluster(
        self,
        cluster: DuplicateCluster,
        collection_name: str
    ) -> MergeResult:
        """
        Merge a cluster of duplicate bullets

        Args:
            cluster: DuplicateCluster to merge
            collection_name: Collection name

        Returns:
            MergeResult with merged bullet
        """
        if len(cluster.bullets) < 2:
            raise ValueError("Need at least 2 bullets to merge")

        logger.info(f"Merging {len(cluster.bullets)} bullets")

        # Use pre-selected primary or select best
        primary = cluster.primary_bullet

        # Merge metadata from all bullets
        merged_bullet = self._merge_bullets(primary, cluster.bullets)

        # Archive secondary bullets
        archived_ids = []
        for bullet in cluster.bullets:
            if bullet.id != primary.id:
                if self.archive_merged:
                    self._archive_bullet(bullet, merged_into=merged_bullet.id)
                archived_ids.append(bullet.id)

        # Update primary bullet in store
        # Convert collection_name to side and update directly via ChromaDB collection
        side = collection_name.replace("procedural_", "")
        if side in self.store._collections:
            collection = self.store._collections[side]
            # Get embedding for the merged bullet text
            embedding = self.store._embed([merged_bullet.text])[0]
            collection.update(
                ids=[merged_bullet.id],
                documents=[merged_bullet.text],
                embeddings=[embedding],
                metadatas=[merged_bullet.to_metadata()]
            )

        # Delete secondary bullets from store
        if archived_ids and side in self.store._collections:
            collection = self.store._collections[side]
            collection.delete(ids=archived_ids)

        # Record merge history
        merge_history = MergeHistory(
            merge_id=f"merge_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now(),
            primary_bullet_id=merged_bullet.id,
            merged_bullet_ids=[b.id for b in cluster.bullets if b.id != primary.id]
        )
        self.merge_history.append(merge_history)

        # Update stats
        self.stats["total_merges"] += 1
        self.stats["total_bullets_merged"] += len(cluster.bullets) - 1

        logger.info(f"Merge complete: {len(cluster.bullets)} -> 1 bullet")

        return MergeResult(
            merged_bullet=merged_bullet,
            source_bullets=cluster.bullets,
            archived_ids=archived_ids
        )

    def _merge_bullets(
        self,
        primary: Bullet,
        all_bullets: List[Bullet]
    ) -> Bullet:
        """
        Merge multiple bullets into one

        Args:
            primary: Primary bullet (highest quality)
            all_bullets: All bullets in cluster (including primary)

        Returns:
            Merged Bullet
        """
        # Create a copy of primary
        merged = Bullet(
            id=primary.id,
            text=primary.text,
            side=primary.side,
            type=primary.type,
            tags=list(primary.tags),
            confidence=primary.confidence,
            helpful_count=primary.helpful_count,
            harmful_count=primary.harmful_count,
            status=primary.status,
            created_at=primary.created_at,
            last_used_at=primary.last_used_at,
            source_trace_id=primary.source_trace_id,
        )

        # Merge scores from all bullets
        total_helpful = 0
        total_harmful = 0
        all_tags = set(merged.tags)
        weighted_confidence_sum = 0.0
        total_weight = 0

        earliest_created = merged.created_at
        most_recent_used = merged.last_used_at

        for bullet in all_bullets:
            # Accumulate scores
            total_helpful += bullet.helpful_count
            total_harmful += bullet.harmful_count

            # Merge tags
            all_tags.update(bullet.tags)

            # Weighted confidence (by usage count)
            weight = bullet.helpful_count + bullet.harmful_count
            if weight > 0:
                weighted_confidence_sum += bullet.confidence * weight
                total_weight += weight

            # Track timestamps
            if bullet.created_at < earliest_created:
                earliest_created = bullet.created_at

            if bullet.last_used_at:
                if most_recent_used is None or bullet.last_used_at > most_recent_used:
                    most_recent_used = bullet.last_used_at

        # Update merged bullet
        merged.helpful_count = total_helpful
        merged.harmful_count = total_harmful
        merged.tags = sorted(list(all_tags))

        # Recalculate confidence (weighted average)
        if total_weight > 0:
            merged.confidence = weighted_confidence_sum / total_weight
        else:
            # No usage, keep primary's confidence
            merged.confidence = primary.confidence

        # Update timestamps
        merged.created_at = earliest_created
        merged.last_used_at = most_recent_used

        return merged

    def _archive_bullet(self, bullet: Bullet, merged_into: str):
        """Archive a merged bullet for recovery"""
        import os

        # Create archive directory if needed
        os.makedirs(self.archive_path, exist_ok=True)

        # Archive file path
        archive_file = os.path.join(
            self.archive_path,
            f"{bullet.id}.json"
        )

        # Archive data
        archive_data = {
            "bullet": bullet.to_dict(),
            "archived_at": datetime.now().isoformat(),
            "merged_into": merged_into,
            "reason": "deduplication"
        }

        # Write to file
        with open(archive_file, 'w') as f:
            json.dump(archive_data, f, indent=2)

        logger.debug(f"Archived bullet {bullet.id} to {archive_file}")

    def merge_bullets_list(
        self,
        bullets: List[Bullet],
        collection_name: str
    ) -> MergeResult:
        """
        Merge a list of bullets (convenience method)

        Args:
            bullets: List of bullets to merge
            collection_name: Collection name

        Returns:
            MergeResult
        """
        from .deduplicator import DuplicateCluster

        # Create a cluster
        cluster = DuplicateCluster(
            bullets=bullets,
            similarity_scores=[0.95] * (len(bullets) - 1)  # Dummy scores
        )

        return self.merge_cluster(cluster, collection_name)

    def get_merge_history(self, limit: int = 10) -> List[MergeHistory]:
        """Get recent merge history"""
        return self.merge_history[-limit:]

    def restore_bullet(self, bullet_id: str, collection_name: str) -> Optional[Bullet]:
        """
        Restore an archived bullet

        Args:
            bullet_id: ID of bullet to restore
            collection_name: Collection to restore to

        Returns:
            Restored Bullet or None if not found
        """
        import os

        archive_file = os.path.join(self.archive_path, f"{bullet_id}.json")

        if not os.path.exists(archive_file):
            logger.warning(f"Archive file not found: {archive_file}")
            return None

        # Load archive data
        with open(archive_file, 'r') as f:
            archive_data = json.load(f)

        # Reconstruct bullet
        bullet_data = archive_data["bullet"]
        bullet = Bullet.from_dict(bullet_data)

        # Add back to store
        self.store.add(
            collection_name=collection_name,
            ids=[bullet.id],
            documents=[bullet.text],
            metadatas=[bullet.to_metadata()]
        )

        logger.info(f"Restored bullet {bullet_id}")

        return bullet

    def get_stats(self) -> Dict[str, Any]:
        """Get merge statistics"""
        return {
            **self.stats,
            "merge_history_count": len(self.merge_history),
            "archive_enabled": self.archive_merged,
        }
