"""High-level Maintenance API"""
import logging
from typing import Dict, Any, Optional

from .procedural_memory import ProceduralMemory
from .deduplicator import Deduplicator
from .bullet_merger import BulletMerger
from .quality_analyzer import QualityAnalyzer, PrunePolicy
from .pruner import Pruner

logger = logging.getLogger(__name__)


async def run_deduplication(
    memory: ProceduralMemory,
    collection: str = "procedural_left",
    threshold: float = 0.90
) -> Dict[str, Any]:
    """
    Run deduplication on a collection

    Args:
        memory: ProceduralMemory instance
        collection: Collection name
        threshold: Similarity threshold

    Returns:
        Results dict
    """
    logger.info(f"Running deduplication on {collection}")

    # Initialize components
    deduplicator = Deduplicator(memory.store, {"dedup_threshold": threshold})
    merger = BulletMerger(memory.store)

    # Find duplicates
    clusters = deduplicator.find_duplicates(collection, threshold=threshold)

    # Merge clusters
    merged_count = 0
    for cluster in clusters:
        merger.merge_cluster(cluster, collection)
        merged_count += len(cluster.bullets) - 1

    logger.info(f"Deduplication complete: {merged_count} bullets merged")

    return {
        "duplicates_found": len(clusters),
        "bullets_merged": merged_count,
        "collection": collection,
        "threshold": threshold,
    }


async def run_pruning(
    memory: ProceduralMemory,
    collection: str = "procedural_left",
    policy: str = "balanced",
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Run pruning on a collection

    Args:
        memory: ProceduralMemory instance
        collection: Collection name
        policy: Pruning policy (aggressive/balanced/conservative)
        dry_run: If True, only analyze without pruning

    Returns:
        Results dict
    """
    logger.info(f"Running pruning on {collection} (policy={policy}, dry_run={dry_run})")

    # Initialize components
    analyzer = QualityAnalyzer({"prune_policy": policy})
    pruner = Pruner(memory.store, analyzer)

    # Run pruning
    prune_policy = PrunePolicy(policy)
    result = pruner.prune_collection(
        collection_name=collection,
        policy=prune_policy,
        dry_run=dry_run,
        force=True
    )

    logger.info(
        f"Pruning complete: {result.bullets_pruned} bullets pruned "
        f"(backup: {result.backup_id})"
    )

    return {
        "candidates_found": result.candidates_found,
        "bullets_pruned": result.bullets_pruned,
        "backup_id": result.backup_id,
        "policy": policy,
        "dry_run": dry_run,
        "prune_by_reason": result.prune_by_reason,
    }


async def run_full_maintenance(
    memory: ProceduralMemory,
    collections: Optional[list] = None,
    dedup_threshold: float = 0.90,
    prune_policy: str = "balanced"
) -> Dict[str, Any]:
    """
    Run full maintenance (deduplication + pruning) on collections

    Args:
        memory: ProceduralMemory instance
        collections: List of collection names (default: all three)
        dedup_threshold: Deduplication similarity threshold
        prune_policy: Pruning policy

    Returns:
        Combined results dict
    """
    collections = collections or ["procedural_left", "procedural_right", "procedural_shared"]

    logger.info(f"Running full maintenance on {len(collections)} collections")

    total_merged = 0
    total_pruned = 0

    for collection in collections:
        # Deduplication
        dedup_result = await run_deduplication(memory, collection, dedup_threshold)
        total_merged += dedup_result["bullets_merged"]

        # Pruning
        prune_result = await run_pruning(memory, collection, prune_policy, dry_run=False)
        total_pruned += prune_result["bullets_pruned"]

    logger.info(
        f"Full maintenance complete: {total_merged} merged, {total_pruned} pruned"
    )

    return {
        "collections_processed": collections,
        "total_bullets_merged": total_merged,
        "total_bullets_pruned": total_pruned,
        "dedup_threshold": dedup_threshold,
        "prune_policy": prune_policy,
    }
