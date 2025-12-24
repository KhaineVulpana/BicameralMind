"""MCP Learning Integration - Connects tool execution to learning pipeline"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from core.memory import ProceduralMemory, LearningPipeline, Hemisphere
from core.meta_controller import MetaController
from .mcp_client import MCPClient
from .tool_executor import ToolExecutor, ToolExecutionContext
from .mcp_trace_generator import MCPTraceGenerator, generate_trace_from_tool_result

logger = logging.getLogger(__name__)


@dataclass
class MCPLearningResult:
    """Result from MCP tool execution with learning"""
    tool_result: Any  # MCPToolResult
    trace: Any  # ExecutionTrace
    learning_result: Any  # LearningResult
    tick_rate: float
    bullets_updated: List[str] = field(default_factory=list)
    insights_extracted: int = 0


class MCPLearningIntegration:
    """
    Integrates MCP tool execution with learning pipeline

    Orchestrates:
    1. Tool execution
    2. Trace generation
    3. Novelty calculation
    4. Learning from execution
    5. Bullet updates
    """

    def __init__(
        self,
        mcp_client: MCPClient,
        procedural_memory: ProceduralMemory,
        meta_controller: MetaController,
        learning_pipeline: LearningPipeline,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize MCP learning integration

        Args:
            mcp_client: Connected MCP client
            procedural_memory: Procedural memory system
            meta_controller: Meta-controller for novelty calculation
            learning_pipeline: Learning pipeline
            config: Optional configuration
        """
        self.mcp_client = mcp_client
        self.procedural_memory = procedural_memory
        self.meta_controller = meta_controller
        self.learning_pipeline = learning_pipeline

        self.config = config or {}
        self.auto_learn = self.config.get("auto_learn", True)
        self.learn_on_success = self.config.get("learn_on_success", True)
        self.learn_on_failure = self.config.get("learn_on_failure", True)

        # Components
        self.tool_executor = ToolExecutor(mcp_client)
        self.trace_generator = MCPTraceGenerator()

        # Statistics
        self.stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "learning_sessions": 0,
            "bullets_created": 0,
            "bullets_promoted": 0,
        }

    async def execute_with_learning(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        hemisphere: str = "left",
        expected_success: bool = True,
        confidence: float = 0.5,
        timeout: Optional[float] = None
    ) -> MCPLearningResult:
        """
        Execute tool and automatically learn from the result

        Args:
            tool_name: Tool to execute
            parameters: Tool parameters
            hemisphere: Which hemisphere is executing ("left" or "right")
            expected_success: Expected outcome for novelty calculation
            confidence: Execution confidence (0.0-1.0)
            timeout: Optional timeout override

        Returns:
            MCPLearningResult with tool result and learning details
        """
        logger.info(f"Executing {tool_name} with learning (hemisphere: {hemisphere})")

        # Step 1: Retrieve relevant bullets
        bullets_used, bullet_ids = await self._retrieve_bullets(
            tool_name, parameters, hemisphere
        )

        # Step 2: Build execution context
        context = ToolExecutionContext(
            tool_name=tool_name,
            parameters=parameters,
            hemisphere=hemisphere,
            confidence=confidence,
            expected_success=expected_success,
            bullets_used=bullet_ids,
        )

        # Step 3: Execute tool
        execution_result = await self.tool_executor.execute(context, timeout=timeout)

        self.stats["total_executions"] += 1
        if execution_result.tool_result.success:
            self.stats["successful_executions"] += 1
        else:
            self.stats["failed_executions"] += 1

        # Step 4: Generate trace
        trace = self.trace_generator.generate(execution_result)

        # Step 5: Learn from execution (if enabled)
        learning_result = None
        tick_rate = 0.0
        bullets_updated = []

        if self.auto_learn and self._should_learn(execution_result.tool_result.success):
            try:
                learning_result = await self._learn_from_execution(
                    trace, expected_success
                )

                tick_rate = learning_result.tick_rate
                bullets_updated = bullet_ids

                self.stats["learning_sessions"] += 1
                if learning_result.bullets_added:
                    self.stats["bullets_created"] += learning_result.bullets_added

                logger.info(
                    f"Learning complete: tick_rate={tick_rate:.2f}, "
                    f"insights={learning_result.insights_extracted}"
                )

            except Exception as e:
                logger.error(f"Learning failed: {e}")
                # Continue even if learning fails

        # Step 6: Record outcomes for bullets
        if bullet_ids:
            helpful = execution_result.tool_result.success
            self.procedural_memory.record_outcome(bullet_ids, helpful=helpful)

            if helpful:
                logger.debug(f"Recorded helpful outcome for {len(bullet_ids)} bullets")
            else:
                logger.debug(f"Recorded harmful outcome for {len(bullet_ids)} bullets")

        return MCPLearningResult(
            tool_result=execution_result.tool_result,
            trace=trace,
            learning_result=learning_result,
            tick_rate=tick_rate,
            bullets_updated=bullets_updated,
            insights_extracted=learning_result.insights_extracted if learning_result else 0,
        )

    async def _retrieve_bullets(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        hemisphere: str
    ) -> tuple[List[Any], List[str]]:
        """
        Retrieve relevant bullets for tool execution

        Args:
            tool_name: Tool name
            parameters: Tool parameters
            hemisphere: Hemisphere

        Returns:
            Tuple of (bullets, bullet_ids)
        """
        # Build query for retrieval
        query = f"Using {tool_name} tool successfully"

        # Add parameter context
        if parameters:
            param_strs = [f"{k}={v}" for k, v in list(parameters.items())[:2]]
            query += f" with {', '.join(param_strs)}"

        # Retrieve bullets
        side = Hemisphere.LEFT if hemisphere == "left" else Hemisphere.RIGHT

        bullets, ids = self.procedural_memory.retrieve(
            query=query,
            side=side,
            k=5,
        )

        logger.debug(f"Retrieved {len(bullets)} bullets for {tool_name}")

        return bullets, ids

    def _should_learn(self, success: bool) -> bool:
        """Determine if we should learn from this execution"""
        if success and not self.learn_on_success:
            return False
        if not success and not self.learn_on_failure:
            return False
        return True

    async def _learn_from_execution(
        self,
        trace: Any,  # ExecutionTrace
        expected_success: bool
    ):
        """
        Learn from execution trace

        Args:
            trace: ExecutionTrace from tool execution
            expected_success: Expected outcome

        Returns:
            LearningResult
        """
        logger.debug(f"Learning from trace {trace.trace_id}")

        # Use learning pipeline with automatic tick calculation
        learning_result = await self.learning_pipeline.learn_from_trace_auto_tick(
            trace=trace,
            meta_controller=self.meta_controller,
            expected_success=expected_success,
        )

        return learning_result

    async def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        Get list of available MCP tools

        Returns:
            List of tool metadata dicts
        """
        tools = await self.mcp_client.list_tools()

        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
                "server": tool.server_name,
            }
            for tool in tools
        ]

    def get_tool_usage_stats(self, tool_name: str) -> Dict[str, Any]:
        """
        Get usage statistics for a specific tool

        Args:
            tool_name: Tool name

        Returns:
            Statistics dict
        """
        traces = self.trace_generator.get_traces_by_tool(tool_name)

        if not traces:
            return {
                "tool_name": tool_name,
                "total_uses": 0,
                "success_rate": 0.0,
            }

        total = len(traces)
        successful = sum(1 for t in traces if t.success)

        return {
            "tool_name": tool_name,
            "total_uses": total,
            "successful_uses": successful,
            "failed_uses": total - successful,
            "success_rate": successful / total if total > 0 else 0.0,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get overall integration statistics"""
        stats = dict(self.stats)

        # Add derived stats
        if stats["total_executions"] > 0:
            stats["success_rate"] = (
                stats["successful_executions"] / stats["total_executions"]
            )
        else:
            stats["success_rate"] = 0.0

        # Add component stats
        stats["executor_stats"] = self.tool_executor.get_stats()
        stats["trace_stats"] = self.trace_generator.get_stats()
        stats["mcp_client_stats"] = self.mcp_client.get_stats()

        return stats
