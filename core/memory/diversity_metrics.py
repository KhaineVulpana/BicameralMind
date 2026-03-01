"""Diversity metrics for cross-hemisphere convergence monitoring."""

from typing import Any, Dict, Iterable, List, Optional
import math

from .bullet import Bullet
from .config_utils import get_cross_hemisphere_config
from .procedural_memory import ProceduralMemory


class DiversityMetrics:
    """Compute divergence signals between hemispheres."""

    def __init__(self, memory: Optional[ProceduralMemory] = None, config: Optional[Dict[str, Any]] = None) -> None:
        self.memory = memory
        cross_cfg = get_cross_hemisphere_config(config or (memory.config if memory else {}))
        diversity_cfg = cross_cfg.get("diversity", {}) if cross_cfg else {}
        self.enabled = bool(diversity_cfg.get("enabled", True))
        self.convergence_warning_threshold = float(
            diversity_cfg.get("convergence_warning_threshold", 0.15)
        )

    @staticmethod
    def _tag_distribution(bullets: Iterable[Bullet]) -> Dict[str, float]:
        counts: Dict[str, float] = {}
        for bullet in bullets:
            for tag in bullet.tags:
                counts[tag] = counts.get(tag, 0.0) + 1.0
        total = sum(counts.values()) or 1.0
        return {k: v / total for k, v in counts.items()}

    @staticmethod
    def _cosine_similarity(vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
        keys = set(vec_a) | set(vec_b)
        dot = sum(vec_a.get(k, 0.0) * vec_b.get(k, 0.0) for k in keys)
        norm_a = math.sqrt(sum(vec_a.get(k, 0.0) ** 2 for k in keys))
        norm_b = math.sqrt(sum(vec_b.get(k, 0.0) ** 2 for k in keys))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)

    def tag_divergence(self, left: List[Bullet], right: List[Bullet]) -> float:
        left_dist = self._tag_distribution(left)
        right_dist = self._tag_distribution(right)
        similarity = self._cosine_similarity(left_dist, right_dist)
        return 1.0 - similarity

    def centroid_distance(self, left_texts: List[str], right_texts: List[str]) -> Optional[float]:
        if not self.memory or not self.memory.enabled:
            return None
        if not left_texts or not right_texts:
            return None
        try:
            left_vecs = self.memory.store._embed(left_texts)
            right_vecs = self.memory.store._embed(right_texts)
        except Exception:
            return None

        def _mean(vectors: List[List[float]]) -> List[float]:
            if not vectors:
                return []
            dim = len(vectors[0])
            acc = [0.0] * dim
            for vec in vectors:
                for i in range(dim):
                    acc[i] += vec[i]
            return [v / len(vectors) for v in acc]

        left_mean = _mean(left_vecs)
        right_mean = _mean(right_vecs)
        if not left_mean or not right_mean:
            return None

        dot = sum(a * b for a, b in zip(left_mean, right_mean))
        norm_a = math.sqrt(sum(a * a for a in left_mean))
        norm_b = math.sqrt(sum(b * b for b in right_mean))
        if norm_a == 0.0 or norm_b == 0.0:
            return None
        cosine = dot / (norm_a * norm_b)
        return 1.0 - cosine

    def compute_from_memory(self, limit: int = 200) -> Dict[str, Any]:
        if not self.memory or not self.memory.enabled:
            return {"enabled": False}
        left = self.memory.store.list_bullets("left", limit=limit)
        right = self.memory.store.list_bullets("right", limit=limit)
        left_bullets = [self.memory._convert_bullet(b) for b in left]
        right_bullets = [self.memory._convert_bullet(b) for b in right]

        tag_div = self.tag_divergence(left_bullets, right_bullets)
        centroid = self.centroid_distance(
            [b.text for b in left_bullets],
            [b.text for b in right_bullets],
        )
        return {
            "enabled": True,
            "tag_divergence": tag_div,
            "centroid_distance": centroid,
            "converged": tag_div < self.convergence_warning_threshold,
        }
