# Phase 4: Advanced Deduplication & Pruning - Implementation Guide

Last Updated: December 24, 2025

## Overview

**Phase 4** implements intelligent bullet maintenance through semantic deduplication and quality-based pruning. This ensures the procedural memory stays clean, efficient, and high-quality over time.

**Key Insight**: Memory quality degrades without maintenance. Duplicate bullets waste retrieval capacity. Low-quality bullets pollute the learning signal.

---

## What This Phase Solves

### Problems Without Maintenance

1. **Duplicate Bullets**: Same knowledge expressed differently accumulates
2. **Memory Bloat**: Storage and retrieval become slower over time
3. **Retrieval Noise**: Similar bullets compete, reducing signal quality
4. **Stale Knowledge**: Old, outdated bullets linger indefinitely
5. **Quality Drift**: Harmful bullets accumulate without cleanup

### Goals

1. **Semantic Deduplication**: Merge semantically similar bullets
2. **Quality Pruning**: Remove low-quality, harmful, or outdated bullets
3. **Consolidation**: Combine related bullets into stronger patterns
4. **Efficiency**: Keep memory lean and retrieval fast
5. **Safety**: Never delete without backup, allow recovery

---

## Architecture

```
Maintenance Pipeline
|
+-- Deduplication
|   |
|   +-- Semantic Similarity Detection
|   |   - Embedding comparison
|   |   - Configurable threshold (0.85-0.95)
|   |   - Per-hemisphere or cross-hemisphere
|   |
|   +-- Duplicate Resolution
|   |   - Keep highest quality
|   |   - Merge metadata (scores, tags)
|   |   - Update references
|   |
|   +-- Consolidation
|       - Combine similar bullets
|       - Strengthen shared patterns
|       - Update confidence scores
|
+-- Pruning
|   |
|   +-- Quality Detection
|   |   - Low helpful count
|   |   - High harmful count
|   |   - Never used bullets
|   |   - Age without validation
|   |
|   +-- Pruning Policies
|   |   - Aggressive: Remove quickly
|   |   - Conservative: Keep longer
|   |   - Balanced: Default
|   |
|   +-- Scheduled Cleanup
|       - Daily, weekly, or manual
|       - Per-collection or global
|       - Audit logging
|
+-- Safety & Recovery
    |
    +-- Backup Before Pruning
    +-- Prune History Log
    +-- Recovery Mechanism
    +-- Rollback Support
```

---

## Components

### 1. Semantic Similarity Detector

**Purpose**: Identify semantically duplicate bullets

**Implementation**: [core/memory/deduplicator.py](../core/memory/deduplicator.py)

**Key Features**:
- Cosine similarity between bullet embeddings
- Configurable similarity threshold
- Per-hemisphere or cross-hemisphere detection
- Batch processing for efficiency
- Similarity clustering

**Algorithm**:
```python
def find_duplicates(bullets, threshold=0.90):
    # 1. Get embeddings for all bullets
    embeddings = embed_bullets(bullets)

    # 2. Compute pairwise cosine similarity
    similarity_matrix = cosine_similarity(embeddings)

    # 3. Find pairs above threshold
    duplicates = []
    for i in range(len(bullets)):
        for j in range(i+1, len(bullets)):
            if similarity_matrix[i][j] >= threshold:
                duplicates.append((bullets[i], bullets[j], similarity_matrix[i][j]))

    # 4. Cluster duplicates
    clusters = cluster_duplicates(duplicates)

    return clusters
```

### 2. Bullet Merger

**Purpose**: Consolidate duplicate bullets into single, stronger bullets

**Implementation**: [core/memory/bullet_merger.py](../core/memory/bullet_merger.py)

**Merge Strategy**:
1. **Keep Best**: Retain bullet with highest helpful_count
2. **Merge Metadata**: Combine scores, tags, timestamps
3. **Update References**: Point all trace references to merged bullet
4. **Archive Originals**: Keep in history for recovery

**Merge Logic**:
```python
def merge_bullets(bullet1, bullet2):
    # Keep bullet with higher quality
    if quality_score(bullet1) > quality_score(bullet2):
        primary, secondary = bullet1, bullet2
    else:
        primary, secondary = bullet2, bullet1

    # Merge scores
    primary.helpful_count += secondary.helpful_count
    primary.harmful_count += secondary.harmful_count

    # Merge tags
    primary.tags = list(set(primary.tags + secondary.tags))

    # Update confidence (weighted average)
    total_uses = primary.helpful_count + secondary.helpful_count
    primary.confidence = (
        (primary.confidence * primary.helpful_count +
         secondary.confidence * secondary.helpful_count) / total_uses
    )

    # Archive secondary
    archive_bullet(secondary, merged_into=primary.id)

    return primary
```

### 3. Quality Analyzer

**Purpose**: Identify low-quality bullets for pruning

**Implementation**: [core/memory/quality_analyzer.py](../core/memory/quality_analyzer.py)

**Quality Metrics**:
- **Score Ratio**: helpful_count / (helpful_count + harmful_count)
- **Usage Frequency**: How often retrieved
- **Age**: Time since creation
- **Validation**: helpful_count > quarantine_threshold
- **Recency**: last_used_at timestamp

**Low-Quality Criteria**:
```python
def is_low_quality(bullet, policy="balanced"):
    if policy == "aggressive":
        return (
            bullet.harmful_count > bullet.helpful_count or
            bullet.helpful_count == 0 and age_days(bullet) > 7 or
            bullet.status == "quarantined" and age_days(bullet) > 14
        )

    elif policy == "conservative":
        return (
            bullet.harmful_count > bullet.helpful_count * 2 or
            bullet.helpful_count == 0 and age_days(bullet) > 30 or
            bullet.status == "quarantined" and age_days(bullet) > 60
        )

    else:  # balanced
        return (
            bullet.harmful_count > bullet.helpful_count * 1.5 or
            bullet.helpful_count == 0 and age_days(bullet) > 14 or
            bullet.status == "quarantined" and age_days(bullet) > 30
        )
```

### 4. Maintenance Scheduler

**Purpose**: Automate periodic maintenance tasks

**Implementation**: [core/memory/maintenance_scheduler.py](../core/memory/maintenance_scheduler.py)

**Scheduled Tasks**:
- **Daily**: Quick deduplication (new bullets only)
- **Weekly**: Full deduplication + light pruning
- **Monthly**: Deep analysis + aggressive pruning
- **Manual**: On-demand maintenance

**Configuration**:
```yaml
procedural_memory:
  maintenance:
    enabled: true

    # Deduplication
    deduplicate_enabled: true
    dedup_threshold: 0.90  # Cosine similarity threshold
    dedup_schedule: "daily"  # daily, weekly, manual
    dedup_scope: "per_hemisphere"  # per_hemisphere, cross_hemisphere, all

    # Pruning
    prune_enabled: true
    prune_policy: "balanced"  # aggressive, balanced, conservative
    prune_schedule: "weekly"  # daily, weekly, monthly, manual

    # Safety
    backup_before_prune: true
    max_prune_per_run: 100  # Safety limit
    keep_prune_history: true
    prune_history_days: 90
```

---

## Implementation Details

### Deduplication Workflow

```python
from core.memory import ProceduralMemory, Deduplicator, BulletMerger

# Initialize
memory = ProceduralMemory(config)
deduplicator = Deduplicator(config)
merger = BulletMerger()

# Run deduplication
duplicate_clusters = await deduplicator.find_duplicates(
    collection="procedural_left",
    threshold=0.90,
    min_cluster_size=2
)

print(f"Found {len(duplicate_clusters)} duplicate clusters")

# Merge duplicates
for cluster in duplicate_clusters:
    merged_bullet = merger.merge_cluster(cluster)
    print(f"Merged {len(cluster)} bullets into {merged_bullet.id}")

# Get stats
stats = deduplicator.get_stats()
print(f"Total duplicates removed: {stats['duplicates_removed']}")
print(f"Space saved: {stats['bullets_merged']}")
```

### Pruning Workflow

```python
from core.memory import QualityAnalyzer, Pruner

# Initialize
analyzer = QualityAnalyzer(config)
pruner = Pruner(config)

# Analyze bullet quality
low_quality_bullets = analyzer.find_low_quality(
    collection="procedural_left",
    policy="balanced"
)

print(f"Found {len(low_quality_bullets)} low-quality bullets")

# Backup before pruning
backup_id = pruner.create_backup()

# Prune low-quality bullets
pruned = pruner.prune_bullets(low_quality_bullets)

print(f"Pruned {len(pruned)} bullets")
print(f"Backup ID: {backup_id}")

# If needed, rollback
# pruner.rollback(backup_id)
```

### Scheduled Maintenance

```python
from core.memory import MaintenanceScheduler

# Initialize scheduler
scheduler = MaintenanceScheduler(config, memory)

# Start background maintenance
await scheduler.start()

# Maintenance runs automatically based on schedule

# Manual trigger
await scheduler.run_maintenance(
    tasks=["deduplicate", "prune"],
    force=True
)

# Stop scheduler
scheduler.stop()
```

---

## Safety Mechanisms

### 1. Backup Before Pruning

```python
class Pruner:
    def prune_bullets(self, bullets):
        # ALWAYS backup first
        backup_id = self.create_backup(bullets)

        try:
            # Perform pruning
            pruned = self._execute_prune(bullets)

            # Log to prune history
            self._log_prune(backup_id, pruned)

            return pruned
        except Exception as e:
            # Rollback on error
            self.rollback(backup_id)
            raise
```

### 2. Prune History & Audit Log

Every pruning operation is logged:
```python
{
    "prune_id": "prune_20251224_143022",
    "backup_id": "backup_20251224_143022",
    "timestamp": "2025-12-24T14:30:22Z",
    "collection": "procedural_left",
    "bullets_pruned": 47,
    "policy": "balanced",
    "bullet_ids": ["pb_left_123", "pb_left_456", ...],
    "reason": "scheduled_weekly",
}
```

### 3. Rollback Support

```python
# Rollback to previous state
pruner.rollback(backup_id="backup_20251224_143022")

# Restore specific bullets
pruner.restore_bullets(bullet_ids=["pb_left_123", "pb_left_456"])
```

### 4. Safety Limits

```python
# Maximum bullets to prune in one operation
max_prune_per_run: 100

# Require confirmation for large prunes
if len(bullets_to_prune) > 50:
    require_user_confirmation()
```

---

## Configuration

Add to `config/config.yaml`:

```yaml
procedural_memory:
  enabled: true
  persist_directory: "./data/memory/procedural"

  # Phase 4: Maintenance Configuration
  maintenance:
    enabled: true

    # Deduplication Settings
    dedup_enabled: true
    dedup_threshold: 0.90  # Cosine similarity (0.0-1.0)
    dedup_schedule: "daily"  # daily, weekly, manual
    dedup_scope: "per_hemisphere"  # per_hemisphere, cross_hemisphere, all
    dedup_min_cluster_size: 2

    # Pruning Settings
    prune_enabled: true
    prune_policy: "balanced"  # aggressive, balanced, conservative
    prune_schedule: "weekly"  # daily, weekly, monthly, manual

    # Pruning Thresholds (balanced policy)
    prune_min_age_days: 14  # Minimum age before considering pruning
    prune_harmful_ratio: 1.5  # harmful_count / helpful_count threshold
    prune_quarantine_age_days: 30  # Max age for quarantined bullets

    # Safety Settings
    backup_before_prune: true
    backup_directory: "./data/memory/backups"
    max_prune_per_run: 100
    require_confirmation_threshold: 50
    keep_prune_history: true
    prune_history_days: 90

    # Performance
    batch_size: 100  # Process bullets in batches
    parallel_processing: true
```

---

## Usage Examples

### Example 1: Manual Deduplication

```python
from core.memory import ProceduralMemory
from core.memory.maintenance import run_deduplication

memory = ProceduralMemory(config)

# Run deduplication on left brain
result = await run_deduplication(
    memory=memory,
    collection="procedural_left",
    threshold=0.90
)

print(f"Duplicates found: {result.duplicates_found}")
print(f"Bullets merged: {result.bullets_merged}")
print(f"Space saved: {result.space_saved_mb:.2f} MB")
```

### Example 2: Manual Pruning

```python
from core.memory.maintenance import run_pruning

# Run pruning with balanced policy
result = await run_pruning(
    memory=memory,
    collection="procedural_left",
    policy="balanced",
    dry_run=False  # Set True to preview without pruning
)

print(f"Low-quality bullets found: {result.candidates_found}")
print(f"Bullets pruned: {result.bullets_pruned}")
print(f"Backup ID: {result.backup_id}")
```

### Example 3: Scheduled Maintenance

```python
from core.memory.maintenance import MaintenanceScheduler

scheduler = MaintenanceScheduler(config, memory)

# Start scheduler (runs in background)
await scheduler.start()

# Check maintenance status
status = scheduler.get_status()
print(f"Last maintenance: {status.last_run}")
print(f"Next maintenance: {status.next_run}")
print(f"Tasks completed: {status.tasks_completed}")

# Stop scheduler
scheduler.stop()
```

### Example 4: Recovery

```python
from core.memory.maintenance import Pruner

pruner = Pruner(config, memory)

# List available backups
backups = pruner.list_backups()
for backup in backups:
    print(f"{backup.id}: {backup.timestamp} ({backup.bullet_count} bullets)")

# Restore from backup
pruner.rollback(backup_id="backup_20251224_143022")

# Restore specific bullets
pruner.restore_bullets(["pb_left_123", "pb_left_456"])
```

---

## Performance Considerations

### Deduplication Performance

**Complexity**: O(n^2) for pairwise comparison, O(n log n) with optimizations

**Optimizations**:
1. **Batch Processing**: Process bullets in chunks
2. **Parallel Comparison**: Use multiprocessing for similarity computation
3. **Approximate Nearest Neighbors**: Use FAISS/Annoy for large collections
4. **Incremental Deduplication**: Only check new bullets against existing

### Pruning Performance

**Complexity**: O(n) - linear scan of bullets

**Optimizations**:
1. **Index Queries**: Use metadata indexes (status, age, scores)
2. **Batch Deletion**: Delete in batches, not one-by-one
3. **Lazy Deletion**: Mark as deleted, clean up later

### Memory Usage

- Deduplication: Loads all embeddings into memory (can be large)
- Pruning: Minimal memory overhead
- Backups: Compressed JSON format

---

## Monitoring & Metrics

### Deduplication Metrics

```python
stats = deduplicator.get_stats()

{
    "total_bullets_analyzed": 1523,
    "duplicate_clusters_found": 47,
    "bullets_merged": 94,
    "space_saved_mb": 2.3,
    "avg_cluster_size": 2.0,
    "largest_cluster_size": 5,
    "similarity_threshold": 0.90,
    "execution_time_seconds": 12.4
}
```

### Pruning Metrics

```python
stats = pruner.get_stats()

{
    "total_bullets_analyzed": 1523,
    "low_quality_found": 38,
    "bullets_pruned": 38,
    "prune_policy": "balanced",
    "backup_created": true,
    "backup_id": "backup_20251224_143022",
    "execution_time_seconds": 2.1,
    "by_reason": {
        "harmful_ratio": 15,
        "never_used_old": 12,
        "quarantined_expired": 11
    }
}
```

### Maintenance History

```python
history = scheduler.get_maintenance_history(days=7)

for entry in history:
    print(f"{entry.timestamp}: {entry.task}")
    print(f"  Duplicates: {entry.duplicates_removed}")
    print(f"  Pruned: {entry.bullets_pruned}")
    print(f"  Duration: {entry.duration_seconds}s")
```

---

## Testing

### Unit Tests

```bash
python -m pytest tests/test_deduplicator.py
python -m pytest tests/test_quality_analyzer.py
python -m pytest tests/test_pruner.py
python -m pytest tests/test_maintenance_scheduler.py
```

### Integration Tests

```bash
python tests/test_phase4_maintenance.py
```

Tests:
- Semantic similarity detection
- Duplicate clustering
- Bullet merging
- Quality analysis
- Pruning policies
- Backup and recovery
- Scheduled maintenance

---

## Critical Design Principles

### Deduplication
- ALWAYS use semantic similarity, not string matching
- NEVER merge bullets from different hemispheres (unless cross-hemisphere mode)
- ALWAYS preserve highest quality bullet
- ALWAYS merge metadata (scores, tags)
- NEVER lose information during merge

### Pruning
- ALWAYS backup before pruning
- NEVER prune recently created bullets (< min_age_days)
- ALWAYS respect prune policies (aggressive/balanced/conservative)
- ALWAYS log pruning operations
- NEVER prune without safety limits

### Safety
- ALWAYS create backups before destructive operations
- ALWAYS maintain prune history
- ALWAYS support rollback
- NEVER delete permanently without backup
- ALWAYS provide dry-run mode

---

## Next Steps (Phase 5)

With maintenance complete, the next phase is:

**Phase 5: Cross-Hemisphere Learning**
- Suggestion system between hemispheres
- Teaching mode for knowledge transfer
- Conflict resolution strategies
- Diversity preservation mechanisms

---

## Files Created/Modified

**Created**:
- `core/memory/deduplicator.py` - Semantic similarity detection
- `core/memory/bullet_merger.py` - Bullet consolidation
- `core/memory/quality_analyzer.py` - Quality detection
- `core/memory/pruner.py` - Pruning system
- `core/memory/maintenance_scheduler.py` - Scheduled maintenance
- `core/memory/maintenance.py` - High-level maintenance API
- `tests/test_phase4_maintenance.py` - Test suite
- `examples/maintenance_example.py` - Usage examples

**Modified**:
- `core/memory/__init__.py` - Export maintenance components
- `config/config.yaml` - Maintenance configuration

**Documentation**:
- `docs/PHASE4_DEDUPLICATION_PRUNING.md` - This document

---

**Status**: Phase 4 Implementation Guide Complete

**Next**: Implement deduplicator and quality analyzer
