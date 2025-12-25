"""Semantic Deduplication for Procedural Memory Bullets"""
import logging
from typing import List, Dict, Any, Tuple, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from .bullet import Bullet
from .procedural_store import ProceduralMemoryStore

logger = logging.getLogger(__name__)


@dataclass
class DuplicateCluster:
    """Represents a cluster of duplicate bullets"""
    bullets: List[Bullet]
    similarity_scores: List[float]
    primary_bullet: Optional[Bullet] = None

    def __post_init__(self):
        """Automatically select primary bullet after initialization"""
        if self.primary_bullet is None and self.bullets:
            self.primary_bullet = self._select_primary()

    def _select_primary(self) -> Bullet:
        """Select the highest quality bullet as primary"""
        return max(self.bullets, key=lambda b: self._quality_score(b))

    @staticmethod
    def _quality_score(bullet: Bullet) -> float:
        """Calculate quality score for a bullet"""
        total = bullet.helpful_count + bullet.harmful_count
        if total == 0:
            return 0.0

        # Quality = (helpful ratio) * log(total uses + 1) * confidence
        helpful_ratio = bullet.helpful_count / total
        usage_weight = np.log1p(total)

        return helpful_ratio * usage_weight * bullet.confidence


@dataclass
class DeduplicationResult:
    """Result from deduplication operation"""
    duplicates_found: int
    bullets_merged: int
    clusters: List[DuplicateCluster]
    space_saved_count: int
    execution_time_seconds: float
    timestamp: datetime = field(default_factory=datetime.now)


class Deduplicator:
    """
    Semantic Deduplication System

    Uses embedding similarity to identify and cluster duplicate bullets.
    """

    def __init__(
        self,
        store: ProceduralMemoryStore,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize deduplicator

        Args:
            store: ProceduralStore instance
            config: Configuration dict
        """
        self.store = store
        self.config = config or {}

        # Deduplication settings
        self.threshold = self.config.get("dedup_threshold", 0.90)
        self.min_cluster_size = self.config.get("dedup_min_cluster_size", 2)
        self.batch_size = self.config.get("batch_size", 100)

        # Statistics
        self.stats = {
            "total_runs": 0,
            "total_duplicates_found": 0,
            "total_bullets_merged": 0,
        }

        logger.info(f"Deduplicator initialized (threshold={self.threshold})")

    def find_duplicates(
        self,
        collection_name: str,
        threshold: Optional[float] = None,
        min_cluster_size: Optional[int] = None,
        bullet_ids: Optional[List[str]] = None
    ) -> List[DuplicateCluster]:
        """
        Find duplicate bullets in a collection

        Args:
            collection_name: Collection to search
            threshold: Similarity threshold (default: config value)
            min_cluster_size: Minimum cluster size (default: config value)
            bullet_ids: Optional list of specific bullet IDs to check

        Returns:
            List of DuplicateCluster objects
        """
        start_time = datetime.now()

        threshold = threshold or self.threshold
        min_cluster_size = min_cluster_size or self.min_cluster_size

        logger.info(f"Finding duplicates in {collection_name} (threshold={threshold})")

        # Get all bullets or specific subset
        if bullet_ids:
            bullets = self._get_bullets_by_ids(collection_name, bullet_ids)
        else:
            bullets = self._get_all_bullets(collection_name)

        if len(bullets) < 2:
            logger.info("Not enough bullets to deduplicate")
            return []

        logger.info(f"Analyzing {len(bullets)} bullets")

        # Get embeddings
        embeddings = self._get_embeddings(bullets)

        # Compute similarity matrix
        similarity_matrix = cosine_similarity(embeddings)

        # Find duplicate pairs
        duplicate_pairs = self._find_duplicate_pairs(
            bullets, similarity_matrix, threshold
        )

        logger.info(f"Found {len(duplicate_pairs)} duplicate pairs")

        # Cluster duplicates
        clusters = self._cluster_duplicates(duplicate_pairs, min_cluster_size)

        logger.info(f"Created {len(clusters)} duplicate clusters")

        # Update stats
        self.stats["total_runs"] += 1
        self.stats["total_duplicates_found"] += len(duplicate_pairs)

        execution_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Deduplication complete in {execution_time:.2f}s")

        return clusters

    def _get_all_bullets(self, collection_name: str) -> List[Bullet]:
        """Get all bullets from collection"""
        # Convert collection_name to side (e.g., "procedural_left" -> "left")
        side = collection_name.replace("procedural_", "")

        # Get bullets using the store's list_bullets method
        procedural_bullets = self.store.list_bullets(side=side, limit=10000, include_deprecated=True)

        # Convert ProceduralBullet to Bullet
        from .bullet import BulletType, BulletStatus, Hemisphere

        bullets = []
        for pb in procedural_bullets:
            bullet = Bullet(
                id=pb.id,
                text=pb.text,
                side=Hemisphere(pb.side),
                type=BulletType(pb.type),
                tags=pb.tags or [],
                status=BulletStatus(pb.status),
                confidence=pb.confidence,
                helpful_count=pb.helpful_count,
                harmful_count=pb.harmful_count,
                created_at=datetime.fromisoformat(pb.created_at.replace("Z", "+00:00")) if pb.created_at else datetime.now(),
                last_used_at=datetime.fromisoformat(pb.last_used_at.replace("Z", "+00:00")) if pb.last_used_at else None,
                source_trace_id=pb.source_trace_id,
                metadata=pb.metadata or {}
            )
            bullets.append(bullet)

        return bullets

    def _get_bullets_by_ids(
        self, collection_name: str, bullet_ids: List[str]
    ) -> List[Bullet]:
        """Get specific bullets by IDs"""
        # Get bullets using the store's get_bullets_by_ids method
        procedural_bullets = self.store.get_bullets_by_ids(bullet_ids=bullet_ids)

        # Convert ProceduralBullet to Bullet
        from .bullet import BulletType, BulletStatus, Hemisphere

        bullets = []
        for pb in procedural_bullets:
            bullet = Bullet(
                id=pb.id,
                text=pb.text,
                side=Hemisphere(pb.side),
                type=BulletType(pb.type),
                tags=pb.tags or [],
                status=BulletStatus(pb.status),
                confidence=pb.confidence,
                helpful_count=pb.helpful_count,
                harmful_count=pb.harmful_count,
                created_at=datetime.fromisoformat(pb.created_at.replace("Z", "+00:00")) if pb.created_at else datetime.now(),
                last_used_at=datetime.fromisoformat(pb.last_used_at.replace("Z", "+00:00")) if pb.last_used_at else None,
                source_trace_id=pb.source_trace_id,
                metadata=pb.metadata or {}
            )
            bullets.append(bullet)

        return bullets

    def _metadata_to_bullet(
        self,
        bullet_id: str,
        text: str,
        metadata: Dict[str, Any],
        embedding: Optional[List[float]] = None
    ) -> Bullet:
        """Convert metadata back to Bullet object"""
        from .bullet import BulletType, Hemisphere, BulletStatus

        bullet = Bullet(
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

        # Store embedding if provided
        if embedding:
            bullet._embedding = embedding

        return bullet

    def _get_embeddings(self, bullets: List[Bullet]) -> np.ndarray:
        """Get embeddings for bullets"""
        # Use the store's embedding function to generate embeddings
        texts = [bullet.text for bullet in bullets]
        embeddings = self.store._embed(texts)
        return np.array(embeddings)

    def _text_to_simple_embedding(self, text: str) -> List[float]:
        """Simple text embedding fallback (for testing)"""
        # This is a placeholder - in production, use actual embeddings
        # For now, create a simple hash-based vector
        import hashlib
        hash_obj = hashlib.md5(text.encode())
        hash_bytes = hash_obj.digest()

        # Convert to 384-dimensional vector (matching sentence-transformers)
        embedding = []
        for i in range(384):
            byte_idx = i % len(hash_bytes)
            embedding.append(float(hash_bytes[byte_idx]) / 255.0)

        return embedding

    def _find_duplicate_pairs(
        self,
        bullets: List[Bullet],
        similarity_matrix: np.ndarray,
        threshold: float
    ) -> List[Tuple[int, int, float]]:
        """Find pairs of bullets above similarity threshold"""
        duplicate_pairs = []

        n = len(bullets)
        for i in range(n):
            for j in range(i + 1, n):
                similarity = similarity_matrix[i][j]

                if similarity >= threshold:
                    duplicate_pairs.append((i, j, similarity))

        return duplicate_pairs

    def _cluster_duplicates(
        self,
        pairs: List[Tuple[int, int, float]],
        min_cluster_size: int
    ) -> List[DuplicateCluster]:
        """Cluster duplicate pairs into groups"""
        if not pairs:
            return []

        # Build adjacency graph
        graph: Dict[int, Set[int]] = {}
        similarities: Dict[Tuple[int, int], float] = {}

        for i, j, sim in pairs:
            if i not in graph:
                graph[i] = set()
            if j not in graph:
                graph[j] = set()

            graph[i].add(j)
            graph[j].add(i)
            similarities[(i, j)] = sim
            similarities[(j, i)] = sim

        # Find connected components using DFS
        visited = set()
        clusters = []

        def dfs(node: int, component: Set[int]):
            visited.add(node)
            component.add(node)

            if node in graph:
                for neighbor in graph[node]:
                    if neighbor not in visited:
                        dfs(neighbor, component)

        for node in graph:
            if node not in visited:
                component: Set[int] = set()
                dfs(node, component)

                if len(component) >= min_cluster_size:
                    clusters.append(component)

        # Convert to DuplicateCluster objects
        # We need the original bullets list to get the actual Bullet objects
        # For now, return the indices - caller will map to bullets

        return clusters  # type: ignore

    def create_clusters_from_indices(
        self,
        bullets: List[Bullet],
        cluster_indices: List[Set[int]],
        similarity_matrix: np.ndarray
    ) -> List[DuplicateCluster]:
        """Convert cluster indices to DuplicateCluster objects"""
        clusters = []

        for indices in cluster_indices:
            indices_list = sorted(list(indices))
            cluster_bullets = [bullets[i] for i in indices_list]

            # Get similarity scores within cluster
            scores = []
            for i in range(len(indices_list)):
                for j in range(i + 1, len(indices_list)):
                    idx1, idx2 = indices_list[i], indices_list[j]
                    scores.append(similarity_matrix[idx1][idx2])

            cluster = DuplicateCluster(
                bullets=cluster_bullets,
                similarity_scores=scores
            )
            clusters.append(cluster)

        return clusters

    def get_stats(self) -> Dict[str, Any]:
        """Get deduplication statistics"""
        return {
            **self.stats,
            "threshold": self.threshold,
            "min_cluster_size": self.min_cluster_size,
        }
