"""Reflector: Analyzes execution traces to extract insights.

The Reflector is responsible for:
1. Analyzing what went right/wrong in an execution
2. Extracting causal relationships
3. Identifying new strategies or pitfalls
4. Proposing candidate bullets for the Curator

CRITICAL: The Reflector does NOT update memory directly.
It only proposes insights. The Curator decides what to add.

Following ACE principles:
- Deep analysis when tick rate is high (novelty/failure)
- Shallow analysis when tick rate is low (routine)
- Focus on actionable insights, not summaries
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
from loguru import logger


class OutcomeType(str, Enum):
    """Type of execution outcome."""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    UNCERTAIN = "uncertain"


class InsightType(str, Enum):
    """Type of insight extracted from reflection."""
    STRATEGY = "strategy"           # What worked well
    PITFALL = "pitfall"             # What went wrong
    PATTERN = "pattern"             # Recognized pattern
    TOOL_RULE = "tool_rule"         # Tool usage insight
    HEURISTIC = "heuristic"         # General principle
    EDGE_CASE = "edge_case"         # Boundary condition


@dataclass
class ExecutionTrace:
    """Captured execution trace for reflection.

    This represents a single task execution with all relevant context.
    """
    trace_id: str
    task: str                       # Original task/query
    hemisphere: str                 # left, right, or both

    # Execution details
    steps: List[Dict[str, Any]]     # Step-by-step execution
    bullets_used: List[str]         # Bullet IDs that were retrieved
    tools_called: List[str]         # Tools/APIs used

    # Outcome
    outcome: OutcomeType
    success: bool
    error_message: Optional[str] = None

    # Context
    tick_rate: float = 0.5          # Consciousness tick rate during execution
    confidence: float = 0.5         # Agent's confidence

    # Metadata
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trace_id": self.trace_id,
            "task": self.task,
            "hemisphere": self.hemisphere,
            "steps": self.steps,
            "bullets_used": self.bullets_used,
            "tools_called": self.tools_called,
            "outcome": self.outcome.value,
            "success": self.success,
            "error_message": self.error_message,
            "tick_rate": self.tick_rate,
            "confidence": self.confidence,
            "metadata": self.metadata or {},
        }


@dataclass
class ReflectionInsight:
    """A single insight extracted from reflection.

    This is a candidate for becoming a bullet.
    """
    insight_type: InsightType
    text: str                       # The actual insight
    confidence: float               # How confident we are in this insight

    # Evidence
    source_trace_id: str
    supporting_evidence: List[str]  # Why we think this is true

    # Suggested categorization
    tags: List[str]
    priority: str = "medium"        # low, medium, high

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "insight_type": self.insight_type.value,
            "text": self.text,
            "confidence": self.confidence,
            "source_trace_id": self.source_trace_id,
            "supporting_evidence": self.supporting_evidence,
            "tags": self.tags,
            "priority": self.priority,
        }


class Reflector:
    """Analyzes execution traces to extract actionable insights.

    This is the "reflection" step in the ACE framework.
    The Reflector does NOT modify memory directly - it only
    proposes insights for the Curator to evaluate.
    """

    def __init__(self, llm_client=None):
        """Initialize reflector.

        Args:
            llm_client: Optional LLM for deep reflection
        """
        self.llm = llm_client

    async def reflect(
        self,
        trace: ExecutionTrace,
        depth: str = "medium",
    ) -> List[ReflectionInsight]:
        """Reflect on an execution trace.

        Args:
            trace: Execution trace to analyze
            depth: Reflection depth (shallow, medium, deep)
                   Typically controlled by tick rate:
                   - Low ticks -> shallow (routine)
                   - Medium ticks -> medium (mild novelty)
                   - High ticks -> deep (failure/novelty)

        Returns:
            List of insights extracted from the trace
        """
        logger.debug(
            f" Reflecting on trace {trace.trace_id[:12]}... "
            f"(depth={depth}, outcome={trace.outcome.value})"
        )

        # Choose reflection method based on depth
        if depth == "shallow":
            insights = self._shallow_reflection(trace)
        elif depth == "deep":
            insights = await self._deep_reflection(trace)
        else:  # medium
            insights = self._medium_reflection(trace)

        logger.info(
            f" Extracted {len(insights)} insights from trace "
            f"({trace.outcome.value})"
        )

        return insights

    def _shallow_reflection(self, trace: ExecutionTrace) -> List[ReflectionInsight]:
        """Shallow reflection - quick heuristic analysis.

        Used for routine, low-tick-rate executions.
        Just records success/failure without deep analysis.
        """
        insights = []

        # Simple success/failure recording
        if trace.success:
            # Record that the bullets used were helpful
            if trace.bullets_used:
                insights.append(ReflectionInsight(
                    insight_type=InsightType.STRATEGY,
                    text=f"Successfully completed task using existing strategies",
                    confidence=0.6,
                    source_trace_id=trace.trace_id,
                    supporting_evidence=[
                        f"Task: {trace.task[:100]}",
                        f"Bullets used: {len(trace.bullets_used)}",
                    ],
                    tags=["success", "routine"],
                    priority="low",
                ))
        else:
            # Record failure
            insights.append(ReflectionInsight(
                insight_type=InsightType.PITFALL,
                text=f"Task failed: {trace.error_message or 'unknown error'}",
                confidence=0.5,
                source_trace_id=trace.trace_id,
                supporting_evidence=[
                    f"Task: {trace.task[:100]}",
                    f"Error: {trace.error_message}",
                ],
                tags=["failure", "needs-investigation"],
                priority="medium",
            ))

        return insights

    def _medium_reflection(self, trace: ExecutionTrace) -> List[ReflectionInsight]:
        """Medium reflection - pattern-based analysis.

        Used for medium-tick-rate executions.
        Analyzes patterns and extracts simple insights.
        """
        insights = []

        # Analyze tool usage
        if trace.tools_called:
            for tool in set(trace.tools_called):
                if trace.success:
                    insights.append(ReflectionInsight(
                        insight_type=InsightType.TOOL_RULE,
                        text=f"Tool '{tool}' was successfully used for this task type",
                        confidence=0.7,
                        source_trace_id=trace.trace_id,
                        supporting_evidence=[
                            f"Task: {trace.task[:100]}",
                            f"Tool: {tool}",
                            "Outcome: success",
                        ],
                        tags=[tool, "tool-usage", "success"],
                        priority="medium",
                    ))
                else:
                    insights.append(ReflectionInsight(
                        insight_type=InsightType.PITFALL,
                        text=f"Tool '{tool}' failed - may need different approach or validation",
                        confidence=0.6,
                        source_trace_id=trace.trace_id,
                        supporting_evidence=[
                            f"Task: {trace.task[:100]}",
                            f"Tool: {tool}",
                            f"Error: {trace.error_message}",
                        ],
                        tags=[tool, "tool-usage", "failure"],
                        priority="high",
                    ))

        # Analyze execution steps
        if len(trace.steps) > 0:
            # Look for patterns in successful/failed steps
            successful_steps = [s for s in trace.steps if s.get("success", False)]
            failed_steps = [s for s in trace.steps if not s.get("success", True)]

            if failed_steps:
                # Extract common failure patterns
                for step in failed_steps[:2]:  # Limit to avoid noise
                    insights.append(ReflectionInsight(
                        insight_type=InsightType.PITFALL,
                        text=f"Step failed: {step.get('description', 'unknown')}",
                        confidence=0.65,
                        source_trace_id=trace.trace_id,
                        supporting_evidence=[
                            f"Step: {step.get('description', 'N/A')}",
                            f"Error: {step.get('error', 'N/A')}",
                        ],
                        tags=["step-failure", trace.hemisphere],
                        priority="medium",
                    ))

        return insights

    async def _deep_reflection(self, trace: ExecutionTrace) -> List[ReflectionInsight]:
        """Deep reflection - LLM-powered analysis.

        Used for high-tick-rate executions (novelty, failure, conflict).
        Performs causal analysis and extracts detailed insights.
        """
        if not self.llm:
            logger.warning("Deep reflection requested but no LLM available, falling back to medium")
            return self._medium_reflection(trace)

        insights = []

        # Build detailed prompt for LLM analysis
        prompt = self._build_reflection_prompt(trace)

        try:
            # Query LLM for deep analysis
            response = await self.llm.ainvoke(prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)

            # Parse LLM response into insights
            parsed_insights = self._parse_llm_insights(
                response_text,
                trace.trace_id,
                trace.hemisphere,
            )

            insights.extend(parsed_insights)

        except Exception as e:
            logger.error(f"Deep reflection failed: {e}")
            # Fallback to medium reflection
            insights.extend(self._medium_reflection(trace))

        return insights

    def _build_reflection_prompt(self, trace: ExecutionTrace) -> str:
        """Build detailed reflection prompt for LLM."""

        steps_str = "\n".join([
            f"{i+1}. {step.get('description', 'N/A')} - "
            f"{'OK success' if step.get('success') else 'X failed'}"
            for i, step in enumerate(trace.steps[:10])  # Limit context
        ])

        tools_str = ", ".join(trace.tools_called) if trace.tools_called else "None"

        prompt = f"""Analyze this execution trace and extract actionable insights.

TASK: {trace.task}

OUTCOME: {trace.outcome.value.upper()} (success={trace.success})
{f'ERROR: {trace.error_message}' if trace.error_message else ''}

EXECUTION STEPS:
{steps_str}

TOOLS USED: {tools_str}

BULLETS USED: {len(trace.bullets_used)} procedural bullets were retrieved

CONTEXT:
- Hemisphere: {trace.hemisphere}
- Tick rate: {trace.tick_rate:.2f} (higher = more novelty/conflict)
- Confidence: {trace.confidence:.2f}

Your task: Extract 2-5 actionable insights from this execution.
Focus on:
1. What strategies WORKED and should be remembered
2. What PITFALLS to avoid in the future
3. New PATTERNS or HEURISTICS discovered
4. TOOL-SPECIFIC rules or best practices
5. EDGE CASES or boundary conditions

For each insight, provide:
- TYPE: [strategy/pitfall/pattern/tool_rule/heuristic/edge_case]
- TEXT: [concise, actionable description]
- CONFIDENCE: [0.0-1.0]
- EVIDENCE: [why you believe this]
- TAGS: [relevant tags]
- PRIORITY: [low/medium/high]

Format as:
---
TYPE: strategy
TEXT: When X happens, do Y because Z
CONFIDENCE: 0.8
EVIDENCE: Step 3 succeeded using this approach; similar pattern in step 5
TAGS: tool-name, pattern-type
PRIORITY: high
---

Provide 2-5 insights:"""

        return prompt

    def _parse_llm_insights(
        self,
        response: str,
        trace_id: str,
        hemisphere: str,
    ) -> List[ReflectionInsight]:
        """Parse LLM response into structured insights."""
        insights = []

        # Split by separator
        blocks = response.split("---")

        for block in blocks:
            if not block.strip():
                continue

            # Parse each block
            lines = block.strip().split("\n")
            insight_data = {}

            for line in lines:
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip().lower()
                    value = value.strip()
                    insight_data[key] = value

            # Build insight if we have required fields
            if "type" in insight_data and "text" in insight_data:
                try:
                    insight_type = InsightType(insight_data["type"])
                except ValueError:
                    insight_type = InsightType.HEURISTIC

                insights.append(ReflectionInsight(
                    insight_type=insight_type,
                    text=insight_data["text"],
                    confidence=float(insight_data.get("confidence", 0.7)),
                    source_trace_id=trace_id,
                    supporting_evidence=[
                        insight_data.get("evidence", "No evidence provided")
                    ],
                    tags=insight_data.get("tags", hemisphere).split(","),
                    priority=insight_data.get("priority", "medium"),
                ))

        return insights

    def should_reflect(
        self,
        tick_rate: float,
        outcome: OutcomeType,
    ) -> tuple[bool, str]:
        """Determine if reflection should occur and at what depth.

        This is where consciousness ticks gate reflection.

        Args:
            tick_rate: Current tick rate (0.0 - 1.0+)
            outcome: Execution outcome

        Returns:
            (should_reflect, depth)
        """
        # Always reflect on failures
        if outcome == OutcomeType.FAILURE:
            return (True, "deep")

        # Reflect deeply on high tick rates (novelty/conflict)
        if tick_rate > 0.8:
            return (True, "deep")

        # Medium reflection on moderate tick rates
        if tick_rate > 0.5:
            return (True, "medium")

        # Shallow reflection on low tick rates (routine)
        if tick_rate > 0.2:
            return (True, "shallow")

        # Skip reflection on very routine tasks
        return (False, "none")
