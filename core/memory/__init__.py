"""Procedural Memory System for Bicameral Mind

Complete ACE-style procedural memory with:
- Bullet-based knowledge storage
- Outcome-based learning
- Reflection and curation
- Automatic promotion to shared memory
"""

from .bullet import Bullet, BulletType, BulletStatus, Hemisphere
from .procedural_memory import ProceduralMemory
from .retrieval import MemoryRetriever
from .reflector import Reflector, ExecutionTrace, ReflectionInsight, OutcomeType, InsightType
from .curator import Curator
from .learning_pipeline import LearningPipeline, LearningResult, create_trace

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

    # Utilities
    'create_trace',
]
