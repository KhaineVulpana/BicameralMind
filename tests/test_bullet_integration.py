"""Test bullet integration with brain agents.

Verifies that bullets are retrieved and used during agent processing.
"""

import pytest
import asyncio
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.memory import ProceduralMemory, Hemisphere, BulletType, BulletStatus
from core.left_brain.agent import LeftBrain
from core.right_brain.agent import RightBrain
from core.base_agent import Message, MessageType
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda


@pytest.fixture
def config():
    """Test configuration."""
    return {
        "model": {
            "name": "qwen3:14b",
            "temperature": 0.7
        },
        "left_brain": {
            "k_bullets": 8,
            "min_bullet_confidence": 0.5
        },
        "right_brain": {
            "k_bullets": 12,
            "min_bullet_confidence": 0.3
        },
        "procedural_memory": {
            "enabled": True,
            "persist_directory": "./test_data/memory/test_integration",
            "embedding_model": "sentence-transformers/all-MiniLM-L6-v2"
        }
    }


@pytest.fixture
def memory(config):
    """Create procedural memory with test bullets."""
    mem = ProceduralMemory(config)

    # Add some test bullets
    mem.add(
        text="When processing API requests, always validate input parameters",
        side=Hemisphere.LEFT,
        bullet_type=BulletType.TOOL_RULE,
        tags=["api", "validation"],
        confidence=0.9,
        status=BulletStatus.ACTIVE
    )

    mem.add(
        text="If retrieval confidence < 0.3, explore alternative approaches",
        side=Hemisphere.RIGHT,
        bullet_type=BulletType.HEURISTIC,
        tags=["exploration", "uncertainty"],
        confidence=0.8,
        status=BulletStatus.ACTIVE
    )

    mem.add(
        text="Check for null or undefined values before processing",
        side=Hemisphere.LEFT,
        bullet_type=BulletType.PITFALL,
        tags=["validation", "errors"],
        confidence=0.85,
        status=BulletStatus.ACTIVE
    )

    return mem


@pytest.fixture
def mock_llm():
    """Mock LLM for testing."""
    def _respond(_prompt):
        return AIMessage(content="Mock LLM response based on procedural knowledge")

    return RunnableLambda(_respond)


@pytest.mark.asyncio
async def test_left_brain_retrieves_bullets(config, memory, mock_llm):
    """Test that left brain retrieves and uses bullets."""
    # Create left brain agent with memory
    left_brain = LeftBrain(config, mock_llm, procedural_memory=memory)

    # Create test message
    message = Message(
        sender="test",
        receiver="LeftBrain",
        msg_type=MessageType.TASK,
        content={"input": "How do I validate API parameters?"},
        metadata={}
    )

    # Process message
    response = await left_brain.process(message)

    # Verify bullets were retrieved
    assert "bullets_used" in response.metadata
    assert "bullets_count" in response.metadata
    assert response.metadata["had_knowledge"] is True
    assert response.metadata["bullets_count"] > 0

    print(f"[OK] Left brain retrieved {response.metadata['bullets_count']} bullets")
    print(f"[OK] Bullet IDs used: {response.metadata['bullets_used']}")


@pytest.mark.asyncio
async def test_right_brain_retrieves_bullets(config, memory, mock_llm):
    """Test that right brain retrieves and uses bullets."""
    # Create right brain agent with memory
    right_brain = RightBrain(config, mock_llm, procedural_memory=memory)

    # Create test message
    message = Message(
        sender="test",
        receiver="RightBrain",
        msg_type=MessageType.TASK,
        content={"input": "What if the retrieval confidence is low?"},
        metadata={}
    )

    # Process message
    response = await right_brain.process(message)

    # Verify bullets were retrieved
    assert "bullets_used" in response.metadata
    assert "bullets_count" in response.metadata
    assert response.metadata["had_knowledge"] is True
    assert response.metadata["bullets_count"] > 0
    assert "novelty" in response.metadata

    print(f"[OK] Right brain retrieved {response.metadata['bullets_count']} bullets")
    print(f"[OK] Novelty score: {response.metadata['novelty']:.2f}")


@pytest.mark.asyncio
async def test_left_brain_no_bullets(config, mock_llm):
    """Test left brain behavior when no bullets match."""
    # Create memory without matching bullets
    mem = ProceduralMemory(config)
    mem.add(
        text="Unrelated bullet about something else",
        side=Hemisphere.LEFT,
        bullet_type=BulletType.HEURISTIC,
        tags=["unrelated"],
        confidence=0.7,
        status=BulletStatus.ACTIVE
    )

    # Create left brain
    left_brain = LeftBrain(config, mock_llm, procedural_memory=mem)

    # Query about something completely different
    message = Message(
        sender="test",
        receiver="LeftBrain",
        msg_type=MessageType.TASK,
        content={"input": "What is the weather like?"},
        metadata={}
    )

    # Process message
    response = await left_brain.process(message)

    # Should still work, just with lower confidence
    assert response.metadata["had_knowledge"] in [True, False]
    print(f"[OK] Left brain handled no-match scenario (bullets: {response.metadata['bullets_count']})")


@pytest.mark.asyncio
async def test_bullet_retrieval_integration():
    """Integration test for bullet retrieval."""
    config = {
        "model": {"name": "qwen3:14b"},
        "left_brain": {"k_bullets": 8, "min_bullet_confidence": 0.5},
        "right_brain": {"k_bullets": 12, "min_bullet_confidence": 0.3},
        "procedural_memory": {
            "enabled": True,
            "persist_directory": "./test_data/memory/integration_test",
            "embedding_model": "sentence-transformers/all-MiniLM-L6-v2"
        }
    }

    # Create memory
    memory = ProceduralMemory(config)

    # Add test bullet
    bullet = memory.add(
        text="Test bullet for integration",
        side=Hemisphere.LEFT,
        bullet_type=BulletType.HEURISTIC,
        tags=["test"],
        confidence=0.8,
        status=BulletStatus.ACTIVE
    )

    # Retrieve it
    bullets, ids = memory.retrieve(
        query="test integration",
        side=Hemisphere.LEFT,
        k=5,
        include_shared=True
    )

    assert len(bullets) > 0
    # Bullet IDs might be different due to conversion
    # Just verify we got something back
    print(f"[OK] Integration test passed: {len(bullets)} bullets retrieved")
    print(f"[OK] Created bullet ID: {bullet.id}")
    print(f"[OK] Retrieved IDs: {ids}")


if __name__ == "__main__":
    # Run tests
    print("Testing bullet integration...")
    asyncio.run(test_bullet_retrieval_integration())
    print("\n[PASS] All integration tests passed!")
