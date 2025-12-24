"""Maintenance Scheduler - Automates deduplication and pruning"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from .procedural_memory import ProceduralMemory
from .deduplicator import Deduplicator
from .bullet_merger import BulletMerger
from .quality_analyzer import QualityAnalyzer, PrunePolicy
from .pruner import Pruner

logger = logging.getLogger(__name__)


class MaintenanceSchedule(Enum):
    """Maintenance schedule options"""
    MANUAL = "manual"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class MaintenanceTask(Enum):
    """Types of maintenance tasks"""
    DEDUPLICATE = "deduplicate"
    PRUNE = "prune"
    FULL = "full"  # Both deduplicate and prune


@dataclass
class MaintenanceStatus:
    """Current maintenance status"""
    running: bool
    last_run: Optional[datetime]
    next_run: Optional[datetime]
    tasks_completed: int
    last_result: Optional[Dict[str, Any]] = None


@dataclass
class MaintenanceResult:
    """Result from maintenance operation"""
    task: str
    timestamp: datetime
    collections_processed: List[str]
    duplicates_removed: int
    bullets_pruned: int
    duration_seconds: float
    success: bool
    error: Optional[str] = None


class MaintenanceScheduler:
    """
    Maintenance Scheduler System

    Automates periodic maintenance tasks:
    - Deduplication (daily/weekly)
    - Pruning (weekly/monthly)
    - Full maintenance (combined)
    """

    def __init__(
        self,
        memory: ProceduralMemory,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize maintenance scheduler

        Args:
            memory: ProceduralMemory instance
            config: Configuration dict
        """
        self.memory = memory
        self.config = config or {}

        # Get maintenance config
        maint_config = self.config.get("procedural_memory", {}).get("maintenance", {})

        # Scheduler settings
        self.enabled = maint_config.get("enabled", True)
        self.dedup_enabled = maint_config.get("deduplicate_enabled", True)
        self.prune_enabled = maint_config.get("prune_enabled", True)

        # Schedules
        self.dedup_schedule = MaintenanceSchedule(
            maint_config.get("dedup_schedule", "daily")
        )
        self.prune_schedule = MaintenanceSchedule(
            maint_config.get("prune_schedule", "weekly")
        )

        # Initialize components
        store_config = self.config.get("procedural_memory", {})

        self.deduplicator = Deduplicator(
            self.memory.store,
            {
                "dedup_threshold": maint_config.get("dedup_threshold", 0.90),
                "dedup_min_cluster_size": maint_config.get("dedup_min_cluster_size", 2),
                "batch_size": maint_config.get("batch_size", 100),
            }
        )

        self.merger = BulletMerger(
            self.memory.store,
            {
                "archive_merged_bullets": True,
                "archive_path": maint_config.get("backup_directory", "./data/memory/archive")
            }
        )

        self.analyzer = QualityAnalyzer({
            "prune_policy": maint_config.get("prune_policy", "balanced"),
            "prune_min_age_days": maint_config.get("prune_min_age_days", 14),
            "prune_harmful_ratio": maint_config.get("prune_harmful_ratio", 1.5),
            "prune_quarantine_age_days": maint_config.get("prune_quarantine_age_days", 30),
        })

        self.pruner = Pruner(
            self.memory.store,
            self.analyzer,
            {
                "backup_before_prune": maint_config.get("backup_before_prune", True),
                "backup_directory": maint_config.get("backup_directory", "./data/memory/backups"),
                "max_prune_per_run": maint_config.get("max_prune_per_run", 100),
                "require_confirmation_threshold": maint_config.get("require_confirmation_threshold", 50),
                "keep_prune_history": maint_config.get("keep_prune_history", True),
            }
        )

        # State
        self.running = False
        self.last_dedup: Optional[datetime] = None
        self.last_prune: Optional[datetime] = None
        self.maintenance_task: Optional[asyncio.Task] = None
        self.history: List[MaintenanceResult] = []

        # Statistics
        self.stats = {
            "total_runs": 0,
            "total_duplicates_removed": 0,
            "total_bullets_pruned": 0,
        }

        logger.info(
            f"MaintenanceScheduler initialized "
            f"(dedup={self.dedup_schedule.value}, prune={self.prune_schedule.value})"
        )

    async def start(self):
        """Start the maintenance scheduler"""
        if not self.enabled:
            logger.info("Maintenance scheduler disabled")
            return

        if self.running:
            logger.warning("Maintenance scheduler already running")
            return

        self.running = True
        self.maintenance_task = asyncio.create_task(self._run_scheduler())

        logger.info("Maintenance scheduler started")

    def stop(self):
        """Stop the maintenance scheduler"""
        self.running = False

        if self.maintenance_task:
            self.maintenance_task.cancel()

        logger.info("Maintenance scheduler stopped")

    async def _run_scheduler(self):
        """Main scheduler loop"""
        logger.info("Maintenance scheduler loop started")

        while self.running:
            try:
                # Check if deduplication is due
                if self._should_run_dedup():
                    await self._run_deduplication()

                # Check if pruning is due
                if self._should_run_prune():
                    await self._run_pruning()

                # Sleep for a while before checking again
                await asyncio.sleep(3600)  # Check every hour

            except asyncio.CancelledError:
                logger.info("Maintenance scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Maintenance scheduler error: {e}")
                await asyncio.sleep(3600)  # Wait before retrying

    def _should_run_dedup(self) -> bool:
        """Check if deduplication should run"""
        if not self.dedup_enabled:
            return False

        if self.dedup_schedule == MaintenanceSchedule.MANUAL:
            return False

        if self.last_dedup is None:
            return True

        interval = self._get_schedule_interval(self.dedup_schedule)
        return datetime.now() >= self.last_dedup + interval

    def _should_run_prune(self) -> bool:
        """Check if pruning should run"""
        if not self.prune_enabled:
            return False

        if self.prune_schedule == MaintenanceSchedule.MANUAL:
            return False

        if self.last_prune is None:
            return True

        interval = self._get_schedule_interval(self.prune_schedule)
        return datetime.now() >= self.last_prune + interval

    def _get_schedule_interval(self, schedule: MaintenanceSchedule) -> timedelta:
        """Get timedelta for a schedule"""
        if schedule == MaintenanceSchedule.DAILY:
            return timedelta(days=1)
        elif schedule == MaintenanceSchedule.WEEKLY:
            return timedelta(weeks=1)
        elif schedule == MaintenanceSchedule.MONTHLY:
            return timedelta(days=30)
        else:
            return timedelta(days=365)  # Manual = very long interval

    async def _run_deduplication(self):
        """Run deduplication on all collections"""
        logger.info("Running scheduled deduplication")
        start_time = datetime.now()

        collections = ["procedural_left", "procedural_right", "procedural_shared"]
        total_duplicates = 0

        for collection in collections:
            try:
                # Find duplicates
                clusters = self.deduplicator.find_duplicates(collection)

                # Merge duplicates
                for cluster in clusters:
                    self.merger.merge_cluster(cluster, collection)
                    total_duplicates += len(cluster.bullets) - 1

                logger.info(f"Deduplicated {collection}: {len(clusters)} clusters")

            except Exception as e:
                logger.error(f"Deduplication failed for {collection}: {e}")

        duration = (datetime.now() - start_time).total_seconds()

        # Update state
        self.last_dedup = datetime.now()
        self.stats["total_duplicates_removed"] += total_duplicates
        self.stats["total_runs"] += 1

        # Record result
        result = MaintenanceResult(
            task="deduplicate",
            timestamp=datetime.now(),
            collections_processed=collections,
            duplicates_removed=total_duplicates,
            bullets_pruned=0,
            duration_seconds=duration,
            success=True
        )
        self.history.append(result)

        logger.info(
            f"Deduplication complete: {total_duplicates} duplicates removed in {duration:.2f}s"
        )

    async def _run_pruning(self):
        """Run pruning on all collections"""
        logger.info("Running scheduled pruning")
        start_time = datetime.now()

        collections = ["procedural_left", "procedural_right", "procedural_shared"]
        total_pruned = 0

        for collection in collections:
            try:
                result = self.pruner.prune_collection(
                    collection_name=collection,
                    policy=PrunePolicy.BALANCED,
                    dry_run=False,
                    force=True  # Auto-approve scheduled prunes
                )

                total_pruned += result.bullets_pruned

                logger.info(
                    f"Pruned {collection}: {result.bullets_pruned} bullets "
                    f"(backup: {result.backup_id})"
                )

            except Exception as e:
                logger.error(f"Pruning failed for {collection}: {e}")

        duration = (datetime.now() - start_time).total_seconds()

        # Update state
        self.last_prune = datetime.now()
        self.stats["total_bullets_pruned"] += total_pruned
        self.stats["total_runs"] += 1

        # Record result
        result = MaintenanceResult(
            task="prune",
            timestamp=datetime.now(),
            collections_processed=collections,
            duplicates_removed=0,
            bullets_pruned=total_pruned,
            duration_seconds=duration,
            success=True
        )
        self.history.append(result)

        logger.info(
            f"Pruning complete: {total_pruned} bullets pruned in {duration:.2f}s"
        )

    async def run_maintenance(
        self,
        tasks: Optional[List[str]] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Manually trigger maintenance

        Args:
            tasks: List of task names ["deduplicate", "prune", "full"]
            force: Run even if disabled

        Returns:
            Results dict
        """
        if not self.enabled and not force:
            raise ValueError("Maintenance is disabled. Use force=True to override.")

        tasks = tasks or ["full"]
        results = {}

        for task in tasks:
            if task == "deduplicate" or task == "full":
                await self._run_deduplication()
                results["deduplicate"] = "complete"

            if task == "prune" or task == "full":
                await self._run_pruning()
                results["prune"] = "complete"

        return results

    def get_status(self) -> MaintenanceStatus:
        """Get current maintenance status"""
        next_dedup = None
        if self.last_dedup and self.dedup_schedule != MaintenanceSchedule.MANUAL:
            interval = self._get_schedule_interval(self.dedup_schedule)
            next_dedup = self.last_dedup + interval

        next_prune = None
        if self.last_prune and self.prune_schedule != MaintenanceSchedule.MANUAL:
            interval = self._get_schedule_interval(self.prune_schedule)
            next_prune = self.last_prune + interval

        # Next run is whichever comes first
        next_run = None
        if next_dedup and next_prune:
            next_run = min(next_dedup, next_prune)
        elif next_dedup:
            next_run = next_dedup
        elif next_prune:
            next_run = next_prune

        last_run = None
        if self.last_dedup and self.last_prune:
            last_run = max(self.last_dedup, self.last_prune)
        elif self.last_dedup:
            last_run = self.last_dedup
        elif self.last_prune:
            last_run = self.last_prune

        last_result = None
        if self.history:
            last = self.history[-1]
            last_result = {
                "task": last.task,
                "timestamp": last.timestamp.isoformat(),
                "duplicates_removed": last.duplicates_removed,
                "bullets_pruned": last.bullets_pruned,
                "duration_seconds": last.duration_seconds,
            }

        return MaintenanceStatus(
            running=self.running,
            last_run=last_run,
            next_run=next_run,
            tasks_completed=len(self.history),
            last_result=last_result
        )

    def get_maintenance_history(self, days: int = 7) -> List[MaintenanceResult]:
        """Get maintenance history for the last N days"""
        cutoff = datetime.now() - timedelta(days=days)

        return [
            result for result in self.history
            if result.timestamp >= cutoff
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics"""
        status = self.get_status()

        return {
            **self.stats,
            "enabled": self.enabled,
            "running": self.running,
            "dedup_schedule": self.dedup_schedule.value,
            "prune_schedule": self.prune_schedule.value,
            "last_run": status.last_run.isoformat() if status.last_run else None,
            "next_run": status.next_run.isoformat() if status.next_run else None,
            "tasks_completed": status.tasks_completed,
        }
