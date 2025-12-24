"""MCP Integration Usage Examples"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from integrations.mcp import MCPClient, MCPLearningIntegration
from core.memory import ProceduralMemory, LearningPipeline
from core.meta_controller import MetaController
from core.llm_client import LLMClient


async def example_1_basic_tool_execution():
    """Example 1: Basic MCP tool execution"""
    print("\n" + "=" * 60)
    print("Example 1: Basic Tool Execution")
    print("=" * 60 + "\n")

    # Configure MCP
    config = {
        "mcp": {
            "enabled": True,
            "servers": [
                {
                    "name": "filesystem",
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "./data"],
                    "enabled": True,
                },
            ],
        }
    }

    # Initialize and connect
    client = MCPClient(config)
    await client.connect()

    # List available tools
    tools = await client.list_tools()
    print(f"Available tools: {[t.name for t in tools]}\n")

    # Execute a tool
    result = await client.call_tool(
        tool_name="read_file",
        parameters={"path": "./README.md"}
    )

    print(f"Tool execution result:")
    print(f"  Success: {result.success}")
    print(f"  Execution time: {result.execution_time:.3f}s")
    if result.success:
        print(f"  Output preview: {str(result.output)[:100]}...")
    else:
        print(f"  Error: {result.error}")

    await client.disconnect()


async def example_2_tool_execution_with_learning():
    """Example 2: Tool execution with automatic learning"""
    print("\n" + "=" * 60)
    print("Example 2: Tool Execution with Learning")
    print("=" * 60 + "\n")

    # Initialize components
    memory_config = {
        "procedural_memory": {
            "enabled": True,
            "persist_directory": "./data/memory/procedural",
        }
    }

    llm_config = {
        "model": {
            "name": "llama3:8b",
            "temperature": 0.7,
        }
    }

    mcp_config = {
        "mcp": {
            "enabled": True,
            "servers": [
                {
                    "name": "filesystem",
                    "type": "stdio",
                    "enabled": True,
                },
            ],
        }
    }

    # Create components
    memory = ProceduralMemory(memory_config)
    llm = LLMClient(llm_config)
    meta_controller = MetaController(llm_config, None, None)
    pipeline = LearningPipeline(memory, llm)
    mcp_client = MCPClient(mcp_config)

    await mcp_client.connect()

    # Create learning integration
    mcp_learning = MCPLearningIntegration(
        mcp_client=mcp_client,
        procedural_memory=memory,
        meta_controller=meta_controller,
        learning_pipeline=pipeline,
    )

    # Execute with automatic learning
    print("Executing tool with automatic learning...\n")
    result = await mcp_learning.execute_with_learning(
        tool_name="read_file",
        parameters={"path": "./README.md"},
        hemisphere="left",
        expected_success=True,
        confidence=0.8,
    )

    print(f"Execution Results:")
    print(f"  Tool success: {result.tool_result.success}")
    print(f"  Tick rate (novelty): {result.tick_rate:.2f}")
    print(f"  Insights extracted: {result.insights_extracted}")
    print(f"  Bullets updated: {len(result.bullets_updated)}")

    if result.learning_result:
        print(f"\nLearning Details:")
        print(f"  Reflection depth: {result.learning_result.reflection_depth}")
        print(f"  Bullets added: {result.learning_result.bullets_added}")

    await mcp_client.disconnect()


async def example_3_learning_from_failures():
    """Example 3: Learning from tool failures"""
    print("\n" + "=" * 60)
    print("Example 3: Learning from Failures")
    print("=" * 60 + "\n")

    # Setup (same as example 2)
    memory_config = {"procedural_memory": {"enabled": True}}
    llm_config = {"model": {"name": "llama3:8b"}}
    mcp_config = {"mcp": {"enabled": True, "servers": [{"name": "filesystem", "type": "stdio", "enabled": True}]}}

    memory = ProceduralMemory(memory_config)
    llm = LLMClient(llm_config)
    meta_controller = MetaController(llm_config, None, None)
    pipeline = LearningPipeline(memory, llm)
    mcp_client = MCPClient(mcp_config)
    await mcp_client.connect()

    mcp_learning = MCPLearningIntegration(
        mcp_client=mcp_client,
        procedural_memory=memory,
        meta_controller=meta_controller,
        learning_pipeline=pipeline,
    )

    # Execute tool that will fail
    print("Executing tool with invalid parameters (expected to fail)...\n")
    result = await mcp_learning.execute_with_learning(
        tool_name="read_file",
        parameters={"path": "./this_file_does_not_exist.txt"},
        hemisphere="left",
        expected_success=True,  # We expect it to work, but it will fail
        confidence=0.7,
    )

    print(f"Execution Results:")
    print(f"  Tool success: {result.tool_result.success}")
    print(f"  Error: {result.tool_result.error}")
    print(f"  Tick rate: {result.tick_rate:.2f} (high = high novelty)")
    print(f"  Insights extracted: {result.insights_extracted}")

    print(f"\nLearning from Failure:")
    print(f"  The system learned that this tool call failed")
    print(f"  High tick rate ({result.tick_rate:.2f}) triggered deep reflection")
    print(f"  New insights were extracted about the failure pattern")
    print(f"  Bullets were updated with harmful signal")

    await mcp_client.disconnect()


async def example_4_tool_usage_tracking():
    """Example 4: Track tool usage patterns"""
    print("\n" + "=" * 60)
    print("Example 4: Tool Usage Tracking")
    print("=" * 60 + "\n")

    # Setup
    memory_config = {"procedural_memory": {"enabled": True}}
    llm_config = {"model": {"name": "llama3:8b"}}
    mcp_config = {"mcp": {"enabled": True, "servers": [{"name": "filesystem", "type": "stdio", "enabled": True}]}}

    memory = ProceduralMemory(memory_config)
    llm = LLMClient(llm_config)
    meta_controller = MetaController(llm_config, None, None)
    pipeline = LearningPipeline(memory, llm)
    mcp_client = MCPClient(mcp_config)
    await mcp_client.connect()

    mcp_learning = MCPLearningIntegration(
        mcp_client=mcp_client,
        procedural_memory=memory,
        meta_controller=meta_controller,
        learning_pipeline=pipeline,
    )

    # Execute multiple tool calls
    print("Executing multiple tool calls...\n")

    for i in range(3):
        await mcp_learning.execute_with_learning(
            tool_name="read_file",
            parameters={"path": "./README.md"},
            hemisphere="left",
        )
        print(f"  Execution {i+1} complete")

    # Get statistics
    print("\nTool Usage Statistics:")
    stats = mcp_learning.get_tool_usage_stats("read_file")
    print(f"  Tool: read_file")
    print(f"  Total uses: {stats['total_uses']}")
    print(f"  Success rate: {stats['success_rate']:.1%}")

    # Get overall stats
    print("\nOverall Integration Statistics:")
    overall_stats = mcp_learning.get_stats()
    print(f"  Total executions: {overall_stats['total_executions']}")
    print(f"  Success rate: {overall_stats['success_rate']:.1%}")
    print(f"  Learning sessions: {overall_stats['learning_sessions']}")
    print(f"  Bullets created: {overall_stats['bullets_created']}")

    await mcp_client.disconnect()


async def example_5_hemisphere_specific_learning():
    """Example 5: Different learning for left vs right brain"""
    print("\n" + "=" * 60)
    print("Example 5: Hemisphere-Specific Learning")
    print("=" * 60 + "\n")

    # Setup
    memory_config = {"procedural_memory": {"enabled": True}}
    llm_config = {"model": {"name": "llama3:8b"}}
    mcp_config = {"mcp": {"enabled": True, "servers": [{"name": "filesystem", "type": "stdio", "enabled": True}]}}

    memory = ProceduralMemory(memory_config)
    llm = LLMClient(llm_config)
    meta_controller = MetaController(llm_config, None, None)
    pipeline = LearningPipeline(memory, llm)
    mcp_client = MCPClient(mcp_config)
    await mcp_client.connect()

    mcp_learning = MCPLearningIntegration(
        mcp_client=mcp_client,
        procedural_memory=memory,
        meta_controller=meta_controller,
        learning_pipeline=pipeline,
    )

    # Left hemisphere: Pattern recognition (higher confidence)
    print("Left Hemisphere Execution:")
    left_result = await mcp_learning.execute_with_learning(
        tool_name="read_file",
        parameters={"path": "./README.md"},
        hemisphere="left",
        confidence=0.9,  # High confidence
    )
    print(f"  Confidence: {left_result.context.confidence:.2f}")
    print(f"  Tick rate: {left_result.tick_rate:.2f}")
    print(f"  Insights: {left_result.insights_extracted}")

    # Right hemisphere: Exploration (lower confidence)
    print("\nRight Hemisphere Execution:")
    right_result = await mcp_learning.execute_with_learning(
        tool_name="read_file",
        parameters={"path": "./README.md"},
        hemisphere="right",
        confidence=0.5,  # Lower confidence (exploring)
    )
    print(f"  Confidence: {right_result.context.confidence:.2f}")
    print(f"  Tick rate: {right_result.tick_rate:.2f}")
    print(f"  Insights: {right_result.insights_extracted}")

    print("\nNote:")
    print("  Left brain (pattern recognition) has higher confidence")
    print("  Right brain (exploration) has lower confidence")
    print("  Each hemisphere learns independently")
    print("  Successful patterns promote to shared memory")

    await mcp_client.disconnect()


async def main():
    """Run all examples"""
    print("\nMCP Integration Examples")
    print("=" * 60)

    try:
        await example_1_basic_tool_execution()
        await example_2_tool_execution_with_learning()
        await example_3_learning_from_failures()
        await example_4_tool_usage_tracking()
        await example_5_hemisphere_specific_learning()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\nExample failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
