"""Meta Controller Module - Consciousness Ticks and Novelty Detection"""

from .controller import MetaController, CognitiveMode, TickMetrics
from .novelty_detector import NoveltyDetector, NoveltySignal, NoveltyMeasurement

__all__ = [
    'MetaController',
    'CognitiveMode',
    'TickMetrics',
    'NoveltyDetector',
    'NoveltySignal',
    'NoveltyMeasurement',
]
