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
from .suggestion_store import SuggestionStore, Suggestion
from .suggestion_delivery import SuggestionDelivery, can_deliver_suggestions
from .teaching import TeachingAPI
from .conflict_detector import ConflictDetector
from .diversity_metrics import DiversityMetrics
from .procedure_store import ProcedureStore, Procedure, ProcedureStatus, ProcedureStep, ProcedureStepType
from .episodic_store import EpisodicStore, Episode
from .bullet_formatter import format_bullets_for_prompt, format_bullets_compact, format_bullets_with_metadata

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

    # Phase 6: Cross-hemisphere learning
    'SuggestionStore',
    'Suggestion',
    'SuggestionDelivery',
    'can_deliver_suggestions',
    'TeachingAPI',
    'ConflictDetector',
    'DiversityMetrics',
    'ProcedureStore',
    'Procedure',
    'ProcedureStatus',
    'ProcedureStep',
    'ProcedureStepType',
    'EpisodicStore',
    'Episode',

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
    'format_bullets_for_prompt',
    'format_bullets_compact',
    'format_bullets_with_metadata',
]
