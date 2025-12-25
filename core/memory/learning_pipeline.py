"""Learning Pipeline: Orchestrates Reflection → Curation → Memory Update.

This is the complete learning cycle:

1. Execute task → Generate trace
2. Consciousness ticks determine if/how to reflect
3. Reflector analyzes trace → Extracts insights
4. Curator converts insights → Creates bullets
5. Bullets added to procedural memory (quarantined)
6. Outcomes update bullet scores
7. Successful bullets activate → Promote to shared

This module provides a high-level API for the entire learning process.
"""

from typing import Dict, List, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass
from datetime import datetime
from loguru import logger

if TYPE_CHECKING:
    from core.meta_controller import MetaController

from .reflector import Reflector, ExecutionTrace, ReflectionInsight, OutcomeType
from .curator import Curator
from .procedural_memory import ProceduralMemory
from .bullet import Bullet, Hemisphere
from .suggestion_store import SuggestionStore
from .suggestion_delivery import SuggestionDelivery


@dataclass
class LearningResult:
    """Result of a learning cycle."""

    trace_id: str
    hemisphere: str

    # Reflection
    reflected: bool
    reflection_depth: str
    insights_extracted: int

    # Curation
    bullets_created: int
    bullets_skipped: int

    # Outcomes
    bullets_marked_helpful: int
    bullets_marked_harmful: int

    # Metadata
    timestamp: datetime
    tick_rate: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trace_id": self.trace_id,
            "hemisphere": self.hemisphere,
            "reflected": self.reflected,
            "reflection_depth": self.reflection_depth,
            "insights_extracted": self.insights_extracted,
            "bullets_created": self.bullets_created,
            "bullets_skipped": self.bullets_skipped,
            "bullets_marked_helpful": self.bullets_marked_helpful,
            "bullets_marked_harmful": self.bullets_marked_harmful,
            "timestamp": self.timestamp.isoformat(),
            "tick_rate": self.tick_rate,
        }


class LearningPipeline:
    """Orchestrates the complete learning cycle.

    Usage:
        pipeline = LearningPipeline(memory, llm)

        # After task execution
        trace = ExecutionTrace(...)
        result = await pipeline.learn_from_trace(trace, tick_rate=0.8)

        # Or with explicit outcome signals
        pipeline.record_outcome(bullet_ids, helpful=True)
    """

    def __init__(
        self,
        memory: ProceduralMemory,
        llm_client=None,
    ):
        """Initialize learning pipeline.

        Args:
            memory: ProceduralMemory instance
            llm_client: LLM for deep reflection
        """
        self.memory = memory
        self.reflector = Reflector(llm_client)
        cross_cfg = memory.get_cross_hemisphere_config()
        suggestions_cfg = (cross_cfg or {}).get("suggestions", {}) if cross_cfg else {}
        self.suggestion_store = None
        self.suggestion_delivery = None
        if cross_cfg and cross_cfg.get("enabled") and suggestions_cfg.get("enabled"):
            store_path = suggestions_cfg.get("store_path", "./data/memory/suggestions.jsonl")
            self.suggestion_store = SuggestionStore(store_path)
            self.suggestion_delivery = SuggestionDelivery(memory, self.suggestion_store, cross_cfg)
        self.curator = Curator(memory, suggestion_store=self.suggestion_store, config=cross_cfg)

        # Statistics
        self.learning_history: List[LearningResult] = []

    async def learn_from_trace(
        self,
        trace: ExecutionTrace,
        tick_rate: float,
        auto_add_bullets: bool = True,
    ) -> LearningResult:
        """Complete learning cycle from an execution trace.

        This is the main entry point for learning.

        Args:
            trace: Execution trace to learn from
            tick_rate: Current consciousness tick rate
            auto_add_bullets: If True, automatically add bullets to memory

        Returns:
            LearningResult with statistics
        """
        logger.info(
            f"🎓 Learning from trace {trace.trace_id[:12]}... "
            f"(hemisphere={trace.hemisphere}, tick_rate={tick_rate:.2f})"
        )

        hemisphere = Hemisphere(trace.hemisphere.lower())
        result = LearningResult(
            trace_id=trace.trace_id,
            hemisphere=trace.hemisphere,
            reflected=False,
            reflection_depth="none",
            insights_extracted=0,
            bullets_created=0,
            bullets_skipped=0,
            bullets_marked_helpful=0,
            bullets_marked_harmful=0,
            timestamp=datetime.utcnow(),
            tick_rate=tick_rate,
        )

        # Step 1: Determine if/how to reflect (tick-gated)
        should_reflect, depth = self.reflector.should_reflect(
            tick_rate=tick_rate,
            outcome=trace.outcome,
        )

        if not should_reflect:
            logger.debug("  ⊘ Skipping reflection (tick rate too low)")
            # Still record outcome for bullets that were used
            self._record_trace_outcome(trace, result)
            return result

        result.reflected = True
        result.reflection_depth = depth

        # Step 2: Reflect on execution
        insights = await self.reflector.reflect(trace, depth=depth)
        result.insights_extracted = len(insights)

        if not insights:
            logger.debug("  ⊘ No insights extracted")
            self._record_trace_outcome(trace, result)
            return result

        # Step 3: Curate insights into bullets
        bullets_created = await self.curator.curate(
            insights=insights,
            hemisphere=hemisphere,
            auto_add=auto_add_bullets,
        )

        result.bullets_created = len(bullets_created)
        result.bullets_skipped = len(insights) - len(bullets_created)

        # Step 4: Record outcome for bullets used in execution
        self._record_trace_outcome(trace, result)

        # Log summary
        logger.success(
            f"✓ Learning complete: {result.insights_extracted} insights → "
            f"{result.bullets_created} bullets "
            f"(depth={depth}, +{result.bullets_marked_helpful}/-{result.bullets_marked_harmful})"
        )

        # Track in history
        self.learning_history.append(result)

        return result

    async def learn_from_trace_auto_tick(
        self,
        trace: ExecutionTrace,
        meta_controller: "MetaController",
        expected_success: Optional[bool] = None,
        auto_add_bullets: bool = True,
    ) -> LearningResult:
        """Learning cycle with automatic tick calculation from meta_controller.

        This is a convenience method that automatically calculates the tick rate
        from the execution trace using the meta_controller's novelty detector.

        Args:
            trace: Execution trace to learn from
            meta_controller: MetaController instance for tick calculation
            expected_success: Optional expected outcome for novelty comparison
            auto_add_bullets: If True, automatically add bullets to memory

        Returns:
            LearningResult with statistics
        """

        # Convert trace to dict for novelty detection
        trace_dict = {
            "success": trace.success,
            "confidence": trace.confidence,
            "tools_called": trace.tools_called,
            "steps": trace.steps,
            "error_message": trace.error_message,
        }

        # Calculate tick rate automatically
        tick_rate = meta_controller.calculate_tick_rate_from_trace(
            trace_data=trace_dict,
            expected_success=expected_success,
        )

        logger.debug(f"🔍 Calculated tick_rate={tick_rate:.2f} from trace novelty")

        # Use standard learning pipeline with calculated tick rate
        return await self.learn_from_trace(
            trace=trace,
            tick_rate=tick_rate,
            auto_add_bullets=auto_add_bullets,
        )

    def _record_trace_outcome(
        self,
        trace: ExecutionTrace,
        result: LearningResult,
    ) -> None:
        """Record outcome for bullets used in the trace."""
        if not trace.bullets_used:
            return

        hemisphere = Hemisphere(trace.hemisphere.lower())

        # Outcome is helpful if task succeeded
        helpful = trace.success

        # Record for all bullets that were used
        self.memory.record_outcome(
            bullet_ids=trace.bullets_used,
            helpful=helpful,
            side=hemisphere,
        )

        # Generate cross-hemisphere suggestions from successful bullets
        if helpful and self.suggestion_store:
            self._maybe_generate_suggestions(trace.bullets_used, hemisphere)

        if helpful:
            self._maybe_mark_cross_confirmation(trace.bullets_used)

        # Update result stats
        if helpful:
            result.bullets_marked_helpful = len(trace.bullets_used)
        else:
            result.bullets_marked_harmful = len(trace.bullets_used)

    def _maybe_generate_suggestions(self, bullet_ids: List[str], hemisphere: Hemisphere) -> None:
        """Create suggestions for eligible bullets."""
        bullets = self.memory.get_bullets_by_ids(bullet_ids)
        if not bullets:
            return
        self.curator.generate_suggestions(
            bullets=bullets,
            from_side=hemisphere,
            reason="successful_outcome",
        )

    def _maybe_mark_cross_confirmation(self, bullet_ids: List[str]) -> None:
        """Mark origin bullets as cross-confirmed when taught bullets succeed."""
        bullets = self.memory.get_bullets_by_ids(bullet_ids)
        for bullet in bullets:
            origin_id = bullet.metadata.get("origin_bullet_id") if bullet.metadata else None
            if origin_id:
                self.memory.update_bullet_metadata(origin_id, {"cross_confirmed": True})

    def record_outcome(
        self,
        bullet_ids: List[str],
        helpful: bool,
        hemisphere: Optional[Hemisphere] = None,
    ) -> None:
        """Manually record outcome for bullets.

        Use this when you have explicit outcome signals
        (e.g., from MCP tool execution, user feedback).

        Args:
            bullet_ids: Bullet IDs to update
            helpful: True if outcome was positive
            hemisphere: Optional hemisphere context
        """
        self.memory.record_outcome(
            bullet_ids=bullet_ids,
            helpful=helpful,
            side=hemisphere,
        )

    def deliver_suggestions(
        self,
        tick_profile: Optional[Dict[str, Any]] = None,
        to_side: Optional[str] = None,
    ) -> List[Any]:
        """Deliver pending suggestions under tick-gated conditions."""
        if not self.suggestion_delivery:
            return []
        profile = tick_profile or {"is_idle": True, "pressure": 0.0}
        return self.suggestion_delivery.deliver_pending(profile, to_side=to_side)

    async def run_maintenance(
        self,
        hemisphere: Hemisphere,
        prune: bool = True,
        deduplicate: bool = True,
        promote: bool = True,
    ) -> Dict[str, Any]:
        """Run memory maintenance tasks.

        This should be run periodically (e.g., nightly).

        Args:
            hemisphere: Which hemisphere to maintain
            prune: Prune low-quality bullets
            deduplicate: Remove duplicates
            promote: Check for promotable bullets

        Returns:
            Statistics about maintenance operations
        """
        logger.info(f"🧹 Running maintenance for {hemisphere.value}")

        stats = {
            "hemisphere": hemisphere.value,
            "pruned": 0,
            "deduplicated": 0,
            "promoted": 0,
        }

        # Prune low-quality bullets
        if prune:
            pruned_ids = await self.curator.prune_low_quality(
                hemisphere=hemisphere,
                min_score=-0.5,
                min_age_days=7,
                dry_run=False,
            )
            stats["pruned"] = len(pruned_ids)

        # Deduplicate
        if deduplicate:
            merged_pairs = await self.curator.deduplicate(
                hemisphere=hemisphere,
                similarity_threshold=0.95,
                dry_run=False,
            )
            stats["deduplicated"] = len(merged_pairs)

        # Check for promotable bullets
        if promote:
            promoted_ids = await self.curator.promote_successful_bullets(
                hemisphere=hemisphere,
                promote_threshold=3,
            )
            stats["promoted"] = len(promoted_ids)

        logger.success(
            f"✓ Maintenance complete: "
            f"pruned={stats['pruned']}, "
            f"deduplicated={stats['deduplicated']}, "
            f"promoted={stats['promoted']}"
        )

        return stats

    def get_learning_stats(self) -> Dict[str, Any]:
        """Get statistics about learning history."""
        if not self.learning_history:
            return {"total_cycles": 0}

        total_cycles = len(self.learning_history)
        total_insights = sum(r.insights_extracted for r in self.learning_history)
        total_bullets = sum(r.bullets_created for r in self.learning_history)

        reflected_cycles = sum(1 for r in self.learning_history if r.reflected)
        avg_tick_rate = sum(r.tick_rate for r in self.learning_history) / total_cycles

        return {
            "total_cycles": total_cycles,
            "reflected_cycles": reflected_cycles,
            "total_insights": total_insights,
            "total_bullets": total_bullets,
            "avg_insights_per_cycle": total_insights / total_cycles if total_cycles > 0 else 0,
            "avg_bullets_per_cycle": total_bullets / total_cycles if total_cycles > 0 else 0,
            "avg_tick_rate": avg_tick_rate,
        }

    def clear_history(self) -> None:
        """Clear learning history (for testing/reset)."""
        self.learning_history = []
        logger.info("Cleared learning history")


# Convenience function for building traces
def create_trace(
    task: str,
    hemisphere: str,
    steps: List[Dict[str, Any]],
    bullets_used: List[str],
    success: bool,
    error_message: Optional[str] = None,
    tools_called: Optional[List[str]] = None,
    tick_rate: float = 0.5,
    confidence: float = 0.5,
    metadata: Optional[Dict[str, Any]] = None,
) -> ExecutionTrace:
    """Create an execution trace.

    Helper function to simplify trace creation.

    Args:
        task: Original task/query
        hemisphere: "left", "right", or "both"
        steps: List of execution steps
        bullets_used: Bullet IDs that were retrieved
        success: Whether task succeeded
        error_message: Error if failed
        tools_called: Tools/APIs used
        tick_rate: Consciousness tick rate
        confidence: Agent confidence

    Returns:
        ExecutionTrace instance
    """
    # Determine outcome
    if success:
        outcome = OutcomeType.SUCCESS
    elif error_message:
        outcome = OutcomeType.FAILURE
    else:
        outcome = OutcomeType.UNCERTAIN

    # Generate trace ID
    trace_id = f"trace_{hemisphere}_{int(datetime.utcnow().timestamp() * 1000)}"

    return ExecutionTrace(
        trace_id=trace_id,
        task=task,
        hemisphere=hemisphere,
        steps=steps,
        bullets_used=bullets_used,
        tools_called=tools_called or [],
        outcome=outcome,
        success=success,
        error_message=error_message,
        tick_rate=tick_rate,
        confidence=confidence,
        metadata=metadata or {},
    )
