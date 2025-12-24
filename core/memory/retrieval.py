"""Advanced retrieval patterns for procedural memory.

Provides specialized retrievers for different use cases:
- Tool-specific retrieval
- Tag-based filtering
- Adaptive k selection
- Multi-query fusion
"""

from typing import List, Optional, Tuple, Dict, Any
from loguru import logger

from .bullet import Bullet, BulletType, Hemisphere
from .procedural_memory import ProceduralMemory


class MemoryRetriever:
    """Advanced retrieval strategies for procedural memory."""

    def __init__(self, memory: ProceduralMemory):
        """Initialize retriever with a ProceduralMemory instance."""
        self.memory = memory

    def retrieve_for_tool(
        self,
        tool_name: str,
        query: str,
        side: Hemisphere,
        k: int = 5,
    ) -> Tuple[List[Bullet], List[str]]:
        """Retrieve bullets specifically for a tool.

        Filters for:
        - Tool-specific tags
        - TOOL_RULE type bullets
        - Higher confidence threshold
        """
        # Try with tool tag filter
        bullets, ids = self.memory.retrieve(
            query=f"{tool_name}: {query}",
            side=side,
            tags=[tool_name],
            k=k,
            min_confidence=0.6,
            include_shared=True,
        )

        # If we got results, prioritize tool_rule type
        if bullets:
            bullets.sort(
                key=lambda b: (
                    b.type == BulletType.TOOL_RULE,  # Tool rules first
                    b.score(),  # Then by score
                ),
                reverse=True,
            )

        logger.debug(f"🔧 Retrieved {len(bullets)} tool-specific bullets for {tool_name}")
        return bullets, ids

    def retrieve_for_error(
        self,
        error_type: str,
        error_message: str,
        side: Hemisphere,
        k: int = 5,
    ) -> Tuple[List[Bullet], List[str]]:
        """Retrieve bullets for handling a specific error.

        Prioritizes:
        - PITFALL type bullets (common mistakes)
        - Bullets tagged with error type
        """
        query = f"error: {error_type} {error_message}"

        bullets, ids = self.memory.retrieve(
            query=query,
            side=side,
            tags=[error_type, "error", "pitfall"],
            k=k,
            min_confidence=0.5,
            include_shared=True,
        )

        # Prioritize pitfall bullets
        if bullets:
            bullets.sort(
                key=lambda b: (
                    b.type == BulletType.PITFALL,
                    b.score(),
                ),
                reverse=True,
            )

        logger.debug(f"🚨 Retrieved {len(bullets)} error-handling bullets")
        return bullets, ids

    def retrieve_multi_query(
        self,
        queries: List[str],
        side: Hemisphere,
        k: int = 10,
        fusion_method: str = "rank",
    ) -> Tuple[List[Bullet], List[str]]:
        """Retrieve using multiple queries and fuse results.

        Useful for complex tasks that can be expressed multiple ways.

        Args:
            queries: List of query strings
            side: Hemisphere to query
            k: Total bullets to return
            fusion_method: "rank" or "score"

        Returns:
            Fused list of bullets and their IDs
        """
        if not queries:
            return ([], [])

        # Retrieve for each query
        all_bullets: Dict[str, Bullet] = {}  # id -> bullet
        bullet_scores: Dict[str, float] = {}  # id -> fused score

        k_per_query = max(k, 5)  # Get more per query, then fuse

        for i, query in enumerate(queries):
            bullets, _ = self.memory.retrieve(
                query=query,
                side=side,
                k=k_per_query,
                include_shared=True,
            )

            for rank, bullet in enumerate(bullets):
                if bullet.id not in all_bullets:
                    all_bullets[bullet.id] = bullet
                    bullet_scores[bullet.id] = 0.0

                # Fusion scoring
                if fusion_method == "rank":
                    # Reciprocal rank fusion
                    bullet_scores[bullet.id] += 1.0 / (rank + 60)
                else:  # score
                    # Direct score fusion
                    bullet_scores[bullet.id] += bullet.score()

        # Sort by fused score
        sorted_ids = sorted(
            bullet_scores.keys(),
            key=lambda bid: bullet_scores[bid],
            reverse=True,
        )

        # Take top k
        top_bullets = [all_bullets[bid] for bid in sorted_ids[:k]]
        top_ids = sorted_ids[:k]

        logger.debug(
            f"🔀 Fused {len(queries)} queries into {len(top_bullets)} bullets "
            f"(method={fusion_method})"
        )

        return top_bullets, top_ids

    def retrieve_adaptive(
        self,
        query: str,
        side: Hemisphere,
        min_k: int = 5,
        max_k: int = 20,
        score_threshold: float = 0.5,
    ) -> Tuple[List[Bullet], List[str]]:
        """Adaptively retrieve bullets based on quality.

        Starts with min_k, expands to max_k if needed, stops when
        bullet scores drop below threshold.

        This allows contexts to grow/shrink based on relevance.
        """
        bullets, ids = self.memory.retrieve(
            query=query,
            side=side,
            k=max_k,
            include_shared=True,
        )

        if not bullets:
            return ([], [])

        # Find cutoff point
        cutoff = len(bullets)
        for i, bullet in enumerate(bullets):
            if i >= min_k and bullet.score() < score_threshold:
                cutoff = i
                break

        selected = bullets[:cutoff]
        selected_ids = ids[:cutoff]

        logger.debug(
            f"📊 Adaptive retrieval: {len(selected)}/{len(bullets)} bullets "
            f"(threshold={score_threshold:.2f})"
        )

        return selected, selected_ids

    def retrieve_by_type(
        self,
        query: str,
        side: Hemisphere,
        bullet_types: List[BulletType],
        k: int = 10,
    ) -> Tuple[List[Bullet], List[str]]:
        """Retrieve only specific types of bullets.

        Useful when you know you need specific knowledge:
        - CHECKLISTs for step-by-step tasks
        - EXAMPLEs for similar problems
        - TOOL_RULEs for API calls
        """
        # Retrieve more than k, then filter
        bullets, ids = self.memory.retrieve(
            query=query,
            side=side,
            k=k * 2,
            include_shared=True,
        )

        # Filter by type
        filtered = [b for b in bullets if b.type in bullet_types]
        filtered_ids = [
            bid
            for bid, b in zip(ids, bullets)
            if b.type in bullet_types
        ]

        # Take top k
        result = filtered[:k]
        result_ids = filtered_ids[:k]

        types_str = ", ".join(t.value for t in bullet_types)
        logger.debug(
            f"📌 Type-filtered retrieval: {len(result)} bullets "
            f"(types=[{types_str}])"
        )

        return result, result_ids

    def retrieve_recent(
        self,
        side: Hemisphere,
        k: int = 10,
        min_age_hours: int = 0,
        max_age_hours: int = 24,
    ) -> List[Bullet]:
        """Retrieve recently used or created bullets.

        Useful for reviewing recent learning.

        Note: This doesn't use semantic search, just recency.
        """
        # TODO: Implement time-based retrieval
        # For now, return empty list
        logger.warning("Time-based retrieval not yet implemented")
        return []

    def retrieve_controversial(
        self,
        side: Hemisphere,
        k: int = 10,
    ) -> List[Bullet]:
        """Retrieve bullets with both helpful and harmful signals.

        These are candidates for review/refinement.
        """
        # TODO: Implement controversy detection
        # For now, return empty list
        logger.warning("Controversial bullet detection not yet implemented")
        return []
