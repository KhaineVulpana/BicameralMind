"""Procedural Memory System for Bicameral Mind

Complete ACE-style procedural memory with:
- Bullet-based knowledge storage
- Outcome-based learning
- Reflection and curation
- Automatic promotion to shared memory
- Deduplication and pruning (Phase 4)
"""

from .bullet import Bullet, BulletType, BulletStatus, Hemisphere
from .procedural_memory import ProceduralMemory
from .retrieval import MemoryRetriever
from .reflector import Reflector, ExecutionTrace, ReflectionInsight, OutcomeType, InsightType
from .curator import Curator
from .learning_pipeline import LearningPipeline, LearningResult, create_trace

# Phase 4: Maintenance
from .deduplicator import Deduplicator, DuplicateCluster
from .bullet_merger import BulletMerger, MergeResult
from .quality_analyzer import QualityAnalyzer, PrunePolicy, PruneReason, QualityMetrics
from .pruner import Pruner, PruneResult
from .maintenance_scheduler import MaintenanceScheduler, MaintenanceStatus
from .maintenance import run_deduplication, run_pruning, run_full_maintenance

__all__ = [
    # Core bullet types
    'Bullet',
    'BulletType',
    'BulletStatus',
    'Hemisphere',

    # Memory management
    'ProceduralMemory',
    'MemoryRetriever',

    # Learning cycle (Phase 2)
    'Reflector',
    'Curator',
    'LearningPipeline',

    # Data structures
    'ExecutionTrace',
    'ReflectionInsight',
    'LearningResult',
    'OutcomeType',
    'InsightType',

    # Maintenance (Phase 4)
    'Deduplicator',
    'DuplicateCluster',
    'BulletMerger',
    'MergeResult',
    'QualityAnalyzer',
    'PrunePolicy',
    'PruneReason',
    'QualityMetrics',
    'Pruner',
    'PruneResult',
    'MaintenanceScheduler',
    'MaintenanceStatus',

    # Maintenance utilities
    'run_deduplication',
    'run_pruning',
    'run_full_maintenance',

    # Utilities
    'create_trace',
]
