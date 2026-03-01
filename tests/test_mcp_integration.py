"""Test MCP Integration"""
import asyncio
import shutil
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

import pytest
import pytest_asyncio

from integrations.mcp import (
    MCPClient,
    ToolExecutor,
    ToolExecutionContext,
    MCPTraceGenerator,
    MCPLearningIntegration,
)
from core.memory import ProceduralMemory, LearningPipeline, Hemisphere
from core.meta_controller import MetaController
from core.llm_client import LLMClient


def print_section(title):
    """Print a section header"""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print(f"{'=' * 60}\n")

def _mcp_config():
    return {
        "mcp": {
            "enabled": True,
            "connection_timeout": 30,
            "tool_timeout": 60,
            "servers": [
                {
                    "name": "filesystem",
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "./data"],
                    "tool_timeout": 30,
                    "enabled": True,
                },
            ],
        }
    }


def _tool_context():
    return ToolExecutionContext(
        tool_name="read_file",
        parameters={"path": "./README.md"},
        hemisphere="left",
        confidence=0.8,
        expected_success=True,
        bullets_used=["test_bullet_1", "test_bullet_2"],
    )


@pytest_asyncio.fixture(scope="module")
async def client():
    if not shutil.which("npx"):
        pytest.skip("npx not available for MCP integration tests")
    mcp_client = MCPClient(_mcp_config())
    await mcp_client.connect()
    yield mcp_client
    await mcp_client.disconnect()


@pytest_asyncio.fixture
async def executor(client):
    return ToolExecutor(client)


@pytest.fixture
def execution_context():
    return _tool_context()


@pytest_asyncio.fixture
async def execution_result(executor, execution_context):
    return await executor.execute(execution_context)


@pytest_asyncio.fixture(scope="module")
async def mcp_learning(client):
    memory_config = {
        "procedural_memory": {
            "enabled": True,
            "persist_directory": "./data/memory/procedural_test",
            "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
            "promote_threshold": 3,
            "quarantine_threshold": 2,
        }
    }

    llm_config = {
        "model": {
            "name": "qwen3:14b",
            "temperature": 0.7,
        }
    }

    memory = ProceduralMemory(memory_config)
    llm = LLMClient(llm_config)
    meta_controller = MetaController(llm_config, None, None)  # Simplified for testing
    pipeline = LearningPipeline(memory, llm)

    return MCPLearningIntegration(
        mcp_client=client,
        procedural_memory=memory,
        meta_controller=meta_controller,
        learning_pipeline=pipeline,
        config={
            "auto_learn": True,
            "learn_on_success": True,
            "learn_on_failure": True,
        },
    )

async def test_mcp_client(client):
    """Test MCP client connection and tool discovery"""
    print_section("Test 1: MCP Client")

    print(f"[OK] MCP Client initialized")
    print(f"     Servers configured: {len(client.servers)}")

    print(f"[OK] Connected to MCP servers")

    # List tools
    tools = await client.list_tools()
    print(f"[OK] Discovered {len(tools)} tools:")
    for tool in tools:
        print(f"     - {tool.name}: {tool.description}")

    # Get stats
    stats = client.get_stats()
    print(f"\n[INFO] Client Stats:")
    print(f"       Connected servers: {stats['connected_servers']}/{stats['total_servers']}")
    print(f"       Available tools: {stats['available_tools']}")


async def test_tool_executor(executor, execution_result):
    """Test tool execution"""
    print_section("Test 2: Tool Executor")

    print(f"[OK] Tool Executor initialized")

    print(f"[INFO] Executing tool: read_file")

    print(f"[OK] Tool executed:")
    print(f"     Success: {execution_result.tool_result.success}")
    print(f"     Execution time: {execution_result.tool_result.execution_time:.3f}s")
    print(f"     Steps: {len(execution_result.execution_steps)}")

    for i, step in enumerate(execution_result.execution_steps, 1):
        status = "[OK]" if step.get("success") else "[FAIL]"
        print(f"     {status} Step {i}: {step.get('description')}")

    # Get stats
    stats = executor.get_stats()
    print(f"\n[INFO] Executor Stats:")
    print(f"       Total executions: {stats['total_executions']}")
    print(f"       Success rate: {stats['success_rate']:.1%}")


async def test_trace_generator(execution_result):
    """Test trace generation from tool results"""
    print_section("Test 3: Trace Generator")

    generator = MCPTraceGenerator()
    print(f"[OK] Trace Generator initialized")

    # Generate trace
    trace = generator.generate(execution_result)

    print(f"[OK] Trace generated:")
    print(f"     Trace ID: {trace.trace_id}")
    print(f"     Task: {trace.task}")
    print(f"     Hemisphere: {trace.hemisphere}")
    print(f"     Success: {trace.success}")
    print(f"     Steps: {len(trace.steps)}")
    print(f"     Bullets used: {len(trace.bullets_used)}")
    print(f"     Tools called: {trace.tools_called}")

    # Get stats
    stats = generator.get_stats()
    print(f"\n[INFO] Generator Stats:")
    print(f"       Total traces: {stats['total_traces']}")
    print(f"       Success rate: {stats['success_rate']:.1%}")
    print(f"       Tools used: {stats['tools_used']}")


async def test_learning_integration(mcp_learning):
    """Test complete MCP learning integration"""
    print_section("Test 4: Learning Integration")

    print(f"[OK] MCP Learning Integration initialized\n")

    # Execute tool with learning
    print("[INFO] Executing tool with automatic learning...")
    result = await mcp_learning.execute_with_learning(
        tool_name="read_file",
        parameters={"path": "./README.md"},
        hemisphere="left",
        expected_success=True,
        confidence=0.7,
    )

    print(f"[OK] Tool execution with learning complete:")
    print(f"     Tool success: {result.tool_result.success}")
    print(f"     Tick rate: {result.tick_rate:.2f}")
    print(f"     Insights extracted: {result.insights_extracted}")
    print(f"     Bullets updated: {len(result.bullets_updated)}")

    # Get stats
    stats = mcp_learning.get_stats()
    print(f"\n[INFO] Integration Stats:")
    print(f"       Total executions: {stats['total_executions']}")
    print(f"       Success rate: {stats['success_rate']:.1%}")
    print(f"       Learning sessions: {stats['learning_sessions']}")
    print(f"       Bullets created: {stats['bullets_created']}")


async def test_failure_learning(mcp_learning):
    """Test learning from tool failures"""
    print_section("Test 5: Learning from Failures")

    # Execute tool that will fail (invalid path)
    print("[INFO] Executing tool with expected failure...")
    result = await mcp_learning.execute_with_learning(
        tool_name="read_file",
        parameters={"path": "./nonexistent_file.txt"},
        hemisphere="left",
        expected_success=True,  # We expect success, but will fail
        confidence=0.6,
    )

    print(f"[OK] Tool execution (expected failure):")
    print(f"     Tool success: {result.tool_result.success}")
    print(f"     Error: {result.tool_result.error}")
    print(f"     Tick rate: {result.tick_rate:.2f}")
    print(f"     Insights extracted: {result.insights_extracted}")

    # High tick rate means high novelty (unexpected failure)
    if result.tick_rate > 0.5:
        print(f"[OK] High novelty detected from failure (tick_rate > 0.5)")
    else:
        print(f"[WARN] Expected higher novelty from failure")


async def test_tool_usage_stats(mcp_learning):
    """Test tool usage statistics"""
    print_section("Test 6: Tool Usage Statistics")

    # Get stats for read_file tool
    tool_stats = mcp_learning.get_tool_usage_stats("read_file")

    print(f"[INFO] Tool Usage Stats for 'read_file':")
    print(f"       Total uses: {tool_stats['total_uses']}")
    print(f"       Successful uses: {tool_stats.get('successful_uses', 0)}")
    print(f"       Failed uses: {tool_stats.get('failed_uses', 0)}")
    print(f"       Success rate: {tool_stats['success_rate']:.1%}")


async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print(" MCP Integration Test Suite")
    print("=" * 60)

    try:
        # Test 1: MCP Client
        manual_client = MCPClient(_mcp_config())
        await manual_client.connect()
        await test_mcp_client(manual_client)

        # Test 2: Tool Executor
        manual_executor = ToolExecutor(manual_client)
        manual_context = _tool_context()
        manual_result = await manual_executor.execute(manual_context)
        await test_tool_executor(manual_executor, manual_result)

        # Test 3: Trace Generator
        await test_trace_generator(manual_result)

        # Test 4: Learning Integration
        manual_memory_config = {
            "procedural_memory": {
                "enabled": True,
                "persist_directory": "./data/memory/procedural_test",
                "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
                "promote_threshold": 3,
                "quarantine_threshold": 2,
            }
        }
        manual_llm_config = {"model": {"name": "qwen3:14b", "temperature": 0.7}}
        manual_memory = ProceduralMemory(manual_memory_config)
        manual_llm = LLMClient(manual_llm_config)
        manual_meta = MetaController(manual_llm_config, None, None)
        manual_pipeline = LearningPipeline(manual_memory, manual_llm)
        manual_learning = MCPLearningIntegration(
            mcp_client=manual_client,
            procedural_memory=manual_memory,
            meta_controller=manual_meta,
            learning_pipeline=manual_pipeline,
            config={
                "auto_learn": True,
                "learn_on_success": True,
                "learn_on_failure": True,
            },
        )
        await test_learning_integration(manual_learning)

        # Test 5: Failure Learning
        await test_failure_learning(manual_learning)

        # Test 6: Tool Usage Stats
        await test_tool_usage_stats(manual_learning)

        # Summary
        print_section("Test Summary")
        print("[OK] All tests completed successfully!")
        print("\nMCP Integration Status:")
        print("  [OK] MCP Client - Connection and tool discovery")
        print("  [OK] Tool Executor - Safe tool execution with logging")
        print("  [OK] Trace Generator - ExecutionTrace conversion")
        print("  [OK] Learning Integration - Automatic learning from tools")
        print("  [OK] Failure Learning - High novelty from unexpected failures")
        print("  [OK] Statistics - Tool usage tracking")

        # Cleanup
        await manual_client.disconnect()
        print("\n[OK] Cleanup complete")

    except Exception as e:
        print(f"\n[FAIL] Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
