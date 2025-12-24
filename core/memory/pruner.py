"""Pruner - Removes low-quality bullets from procedural memory"""
import logging
import os
import json
import shutil
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from .bullet import Bullet
from .procedural_store import ProceduralStore
from .quality_analyzer import QualityAnalyzer, PrunePolicy, QualityMetrics, PruneReason

logger = logging.getLogger(__name__)


@dataclass
class PruneResult:
    """Result from pruning operation"""
    candidates_found: int
    bullets_pruned: int
    backup_id: str
    policy: str
    execution_time_seconds: float
    timestamp: datetime = field(default_factory=datetime.now)
    prune_by_reason: Dict[str, int] = field(default_factory=dict)


@dataclass
class BackupMetadata:
    """Metadata for a backup"""
    backup_id: str
    timestamp: datetime
    collection_name: str
    bullet_count: int
    reason: str
    file_path: str


class Pruner:
    """
    Pruner System

    Safely removes low-quality bullets with:
    - Automatic backup before pruning
    - Configurable policies
    - Audit logging
    - Rollback support
    """

    def __init__(
        self,
        store: ProceduralStore,
        analyzer: QualityAnalyzer,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize pruner

        Args:
            store: ProceduralStore instance
            analyzer: QualityAnalyzer instance
            config: Configuration dict
        """
        self.store = store
        self.analyzer = analyzer
        self.config = config or {}

        # Pruning settings
        self.backup_enabled = self.config.get("backup_before_prune", True)
        self.backup_dir = self.config.get("backup_directory", "./data/memory/backups")
        self.max_prune_per_run = self.config.get("max_prune_per_run", 100)
        self.require_confirmation_threshold = self.config.get(
            "require_confirmation_threshold", 50
        )
        self.keep_prune_history = self.config.get("keep_prune_history", True)
        self.history_dir = os.path.join(self.backup_dir, "history")

        # Create directories
        os.makedirs(self.backup_dir, exist_ok=True)
        if self.keep_prune_history:
            os.makedirs(self.history_dir, exist_ok=True)

        # Statistics
        self.stats = {
            "total_prunes": 0,
            "total_bullets_pruned": 0,
            "backups_created": 0,
        }

        logger.info(f"Pruner initialized (max_prune={self.max_prune_per_run})")

    def prune_collection(
        self,
        collection_name: str,
        policy: Optional[PrunePolicy] = None,
        dry_run: bool = False,
        force: bool = False
    ) -> PruneResult:
        """
        Prune low-quality bullets from a collection

        Args:
            collection_name: Collection to prune
            policy: Pruning policy to use
            dry_run: If True, only analyze without pruning
            force: Skip confirmation check

        Returns:
            PruneResult
        """
        start_time = datetime.now()

        logger.info(f"Pruning collection: {collection_name} (dry_run={dry_run})")

        # Get all bullets
        bullets = self._get_all_bullets(collection_name)

        if not bullets:
            logger.info("No bullets to prune")
            return self._empty_result(policy)

        # Find low-quality bullets
        low_quality = self.analyzer.find_low_quality(bullets, policy)

        candidates_found = len(low_quality)
        logger.info(f"Found {candidates_found} low-quality bullets")

        if candidates_found == 0:
            return self._empty_result(policy)

        # Apply safety limit
        if candidates_found > self.max_prune_per_run:
            logger.warning(
                f"Candidate count ({candidates_found}) exceeds limit "
                f"({self.max_prune_per_run}), limiting prune"
            )
            low_quality = low_quality[:self.max_prune_per_run]

        # Check for confirmation requirement
        if (not force and
            candidates_found > self.require_confirmation_threshold and
            not dry_run):
            raise ValueError(
                f"Pruning {candidates_found} bullets requires confirmation. "
                f"Use force=True to proceed."
            )

        if dry_run:
            logger.info("Dry run complete, no bullets pruned")
            execution_time = (datetime.now() - start_time).total_seconds()

            return PruneResult(
                candidates_found=candidates_found,
                bullets_pruned=0,
                backup_id="dry_run",
                policy=policy.value if policy else "unknown",
                execution_time_seconds=execution_time,
                prune_by_reason=self._count_prune_reasons(low_quality)
            )

        # Create backup
        backup_id = ""
        if self.backup_enabled:
            backup_id = self._create_backup(
                collection_name,
                [bullet for bullet, _ in low_quality]
            )

        # Prune bullets
        pruned_count = self._prune_bullets(
            collection_name,
            [bullet for bullet, metrics in low_quality]
        )

        # Log prune operation
        if self.keep_prune_history:
            self._log_prune(
                collection_name=collection_name,
                backup_id=backup_id,
                bullets_pruned=low_quality,
                policy=policy
            )

        # Update stats
        self.stats["total_prunes"] += 1
        self.stats["total_bullets_pruned"] += pruned_count

        execution_time = (datetime.now() - start_time).total_seconds()

        logger.info(
            f"Pruning complete: {pruned_count} bullets removed in {execution_time:.2f}s"
        )

        return PruneResult(
            candidates_found=candidates_found,
            bullets_pruned=pruned_count,
            backup_id=backup_id,
            policy=policy.value if policy else "unknown",
            execution_time_seconds=execution_time,
            prune_by_reason=self._count_prune_reasons(low_quality)
        )

    def _get_all_bullets(self, collection_name: str) -> List[Bullet]:
        """Get all bullets from collection"""
        result = self.store.query(
            collection_name=collection_name,
            query_texts=[""],
            n_results=10000
        )

        if not result or not result.get("ids"):
            return []

        bullets = []
        for i in range(len(result["ids"])):
            metadata = result["metadatas"][i] if result.get("metadatas") else {}

            bullet = self._metadata_to_bullet(
                bullet_id=result["ids"][i],
                text=result["documents"][i],
                metadata=metadata
            )
            bullets.append(bullet)

        return bullets

    def _metadata_to_bullet(
        self,
        bullet_id: str,
        text: str,
        metadata: Dict[str, Any]
    ) -> Bullet:
        """Convert metadata to Bullet object"""
        from .bullet import BulletType, Hemisphere, BulletStatus

        return Bullet(
            id=bullet_id,
            text=text,
            side=Hemisphere(metadata.get("side", "left")),
            bullet_type=BulletType(metadata.get("type", "heuristic")),
            tags=metadata.get("tags", []),
            confidence=metadata.get("confidence", 0.5),
            helpful_count=metadata.get("helpful_count", 0),
            harmful_count=metadata.get("harmful_count", 0),
            status=BulletStatus(metadata.get("status", "active")),
            created_at=datetime.fromisoformat(metadata["created_at"]) if metadata.get("created_at") else datetime.now(),
            last_used_at=datetime.fromisoformat(metadata["last_used_at"]) if metadata.get("last_used_at") else None,
            source_trace_id=metadata.get("source_trace_id"),
        )

    def _create_backup(
        self,
        collection_name: str,
        bullets: List[Bullet]
    ) -> str:
        """Create backup of bullets before pruning"""
        backup_id = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        backup_data = {
            "backup_id": backup_id,
            "timestamp": datetime.now().isoformat(),
            "collection_name": collection_name,
            "bullet_count": len(bullets),
            "bullets": [bullet.to_dict() for bullet in bullets]
        }

        backup_file = os.path.join(self.backup_dir, f"{backup_id}.json")

        with open(backup_file, 'w') as f:
            json.dump(backup_data, f, indent=2)

        self.stats["backups_created"] += 1

        logger.info(f"Created backup: {backup_id} ({len(bullets)} bullets)")

        return backup_id

    def _prune_bullets(
        self,
        collection_name: str,
        bullets: List[Bullet]
    ) -> int:
        """Delete bullets from collection"""
        if not bullets:
            return 0

        bullet_ids = [b.id for b in bullets]

        self.store.delete(
            collection_name=collection_name,
            ids=bullet_ids
        )

        return len(bullets)

    def _log_prune(
        self,
        collection_name: str,
        backup_id: str,
        bullets_pruned: List[Tuple[Bullet, QualityMetrics]],
        policy: Optional[PrunePolicy]
    ):
        """Log pruning operation to history"""
        history_entry = {
            "prune_id": f"prune_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "backup_id": backup_id,
            "timestamp": datetime.now().isoformat(),
            "collection": collection_name,
            "bullets_pruned": len(bullets_pruned),
            "policy": policy.value if policy else "unknown",
            "bullet_ids": [b.id for b, _ in bullets_pruned],
            "prune_reasons": self._count_prune_reasons(bullets_pruned),
        }

        history_file = os.path.join(
            self.history_dir,
            f"prune_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        with open(history_file, 'w') as f:
            json.dump(history_entry, f, indent=2)

    def _count_prune_reasons(
        self,
        bullets_with_metrics: List[Tuple[Bullet, QualityMetrics]]
    ) -> Dict[str, int]:
        """Count bullets by prune reason"""
        counts: Dict[str, int] = {}

        for _, metrics in bullets_with_metrics:
            for reason in metrics.prune_reasons:
                reason_str = reason.value
                counts[reason_str] = counts.get(reason_str, 0) + 1

        return counts

    def _empty_result(self, policy: Optional[PrunePolicy]) -> PruneResult:
        """Create empty result"""
        return PruneResult(
            candidates_found=0,
            bullets_pruned=0,
            backup_id="",
            policy=policy.value if policy else "unknown",
            execution_time_seconds=0.0
        )

    def rollback(self, backup_id: str, collection_name: str) -> int:
        """
        Restore bullets from a backup

        Args:
            backup_id: Backup ID to restore from
            collection_name: Collection to restore to

        Returns:
            Number of bullets restored
        """
        backup_file = os.path.join(self.backup_dir, f"{backup_id}.json")

        if not os.path.exists(backup_file):
            raise FileNotFoundError(f"Backup not found: {backup_id}")

        logger.info(f"Rolling back from backup: {backup_id}")

        with open(backup_file, 'r') as f:
            backup_data = json.load(f)

        bullets_data = backup_data["bullets"]

        # Restore each bullet
        restored_count = 0
        for bullet_data in bullets_data:
            bullet = Bullet.from_dict(bullet_data)

            self.store.add(
                collection_name=collection_name,
                ids=[bullet.id],
                documents=[bullet.text],
                metadatas=[bullet.to_metadata()]
            )
            restored_count += 1

        logger.info(f"Restored {restored_count} bullets")

        return restored_count

    def list_backups(self) -> List[BackupMetadata]:
        """List available backups"""
        backups = []

        if not os.path.exists(self.backup_dir):
            return backups

        for filename in os.listdir(self.backup_dir):
            if not filename.endswith(".json"):
                continue

            filepath = os.path.join(self.backup_dir, filename)

            with open(filepath, 'r') as f:
                data = json.load(f)

            backups.append(BackupMetadata(
                backup_id=data["backup_id"],
                timestamp=datetime.fromisoformat(data["timestamp"]),
                collection_name=data["collection_name"],
                bullet_count=data["bullet_count"],
                reason="prune",
                file_path=filepath
            ))

        # Sort by timestamp (newest first)
        backups.sort(key=lambda b: b.timestamp, reverse=True)

        return backups

    def get_stats(self) -> Dict[str, Any]:
        """Get pruner statistics"""
        return {
            **self.stats,
            "backup_enabled": self.backup_enabled,
            "max_prune_per_run": self.max_prune_per_run,
        }
