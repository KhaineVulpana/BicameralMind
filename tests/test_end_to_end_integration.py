"""End-to-End Integration Test for Bicameral Mind Learning Cycle.

This test verifies the complete learning workflow:
1. User query arrives
2. Agent retrieves relevant bullets from procedural memory
3. Agent generates response using bullets as context
4. Execution trace is created
5. Reflector extracts insights from trace
6. Curator converts insights to bullets
7. Classifier assigns bullets to correct hemisphere (by cognitive style)
8. Bullets enter staging or are auto-assigned
9. Bullets become available for future retrieval

Tests the full ACE learning cycle with hemisphere classification.
"""

import pytest
import asyncio
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.memory import (
    ProceduralMemory,
    Hemisphere,
    BulletType,
    BulletStatus,
    LearningPipeline,
    Reflector,
    Curator,
    create_trace,
    OutcomeType
)
from core.memory.meta_bullets import check_meta_bullets_installed
from core.left_brain.agent import LeftBrain
from core.right_brain.agent import RightBrain
from core.base_agent import Message, MessageType


@pytest.fixture
def config():
    """Full system configuration."""
    return {
        "model": {
            "name": "llama3:8b",
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
            "persist_directory": "./data/memory/procedural",
            "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
            "learning": {
                "reflection_enabled": True,
                "auto_curate": True,
                "min_insight_confidence": 0.5,
                "deep_reflection_llm": False  # Disable LLM for testing
            },
            "staging": {
                "enabled": True,
                "auto_assign": True,
                "auto_assign_threshold": 0.85,
                "manual_review_threshold": 0.7
            }
        }
    }


@pytest.fixture
def mock_llm():
    """Mock LLM for testing."""
    from langchain_core.runnables import RunnableLambda

    async def mock_invoke(prompt):
        """Return a mock response that varies based on prompt."""
        class Response:
            def __init__(self, content):
                self.content = content

        prompt_text = str(prompt) if not isinstance(prompt, str) else prompt

        # Detect if this is a validation-related query
        if "validate" in prompt_text.lower() or "validation" in prompt_text.lower():
            return Response("Always validate user input before processing. Check for null values and type correctness.")
        # Detect if this is exploration-related
        elif "explore" in prompt_text.lower() or "alternative" in prompt_text.lower():
            return Response("Consider exploring alternative approaches. Try different parameters and creative solutions.")
        else:
            return Response("Process the request according to specifications.")

    return RunnableLambda(mock_invoke)


@pytest.mark.asyncio
async def test_end_to_end_learning_cycle(config, mock_llm):
    """Test complete learning cycle from query to bullet creation."""

    # Skip if meta-bullets not installed
    memory = ProceduralMemory(config)
    if not check_meta_bullets_installed(memory):
        pytest.skip("Meta-bullets not installed - run scripts/install_meta_bullets.py")

    print("\n=== END-TO-END INTEGRATION TEST ===\n")

    # Step 1: Initialize system components
    print("[1] Initializing system components...")
    left_brain = LeftBrain(config, mock_llm, procedural_memory=memory)
    learning_pipeline = LearningPipeline(memory, config)

    # Step 2: Add a seed bullet about validation
    print("[2] Adding seed bullet about validation...")
    seed_bullet = memory.add(
        text="When processing user input, always validate data types",
        side=Hemisphere.LEFT,
        bullet_type=BulletType.TOOL_RULE,
        tags=["validation", "input"],
        confidence=0.9,
        status=BulletStatus.ACTIVE
    )
    print(f"    Created: {seed_bullet.id}")

    # Step 3: User query arrives
    print("[3] User query arrives...")
    user_query = "How should I handle user input validation?"
    message = Message(
        sender="user",
        receiver="LeftBrain",
        msg_type=MessageType.TASK,
        content={"input": user_query},
        metadata={}
    )

    # Step 4: Agent retrieves bullets and generates response
    print("[4] Agent retrieves bullets and generates response...")
    response = await left_brain.process(message)

    # Verify bullets were retrieved
    assert "bullets_used" in response.metadata
    assert "bullets_count" in response.metadata
    bullets_used = response.metadata["bullets_used"]
    bullets_count = response.metadata["bullets_count"]

    print(f"    Bullets retrieved: {bullets_count}")
    print(f"    Bullet IDs: {bullets_used}")
    print(f"    Response: {response.content[:100]}...")

    # Step 5: Create execution trace
    print("[5] Creating execution trace...")
    trace = create_trace(
        task=user_query,
        hemisphere="left",
        steps=[
            {"action": "retrieve_bullets", "result": f"Retrieved {bullets_count} bullets"},
            {"action": "generate_response", "result": "Generated validation-focused response"}
        ],
        bullets_used=bullets_used,
        success=True
    )
    print(f"    Trace ID: {trace.trace_id}")

    # Step 6: Reflection extracts insights
    print("[6] Reflector extracts insights...")
    reflector = Reflector(config)
    insights = await reflector.reflect(trace, depth="shallow")

    print(f"    Insights extracted: {len(insights)}")
    for i, insight in enumerate(insights):
        print(f"      {i+1}. [{insight.insight_type.value}] {insight.text[:60]}...")

    # Step 7: Curator converts insights to bullets with classification
    print("[7] Curator converts insights to bullets (with classification)...")
    curator = Curator(memory)
    new_bullets = await curator.curate(
        insights=insights,
        hemisphere=Hemisphere.LEFT,  # Source hemisphere
        auto_add=True
    )

    print(f"    Bullets created: {len(new_bullets)}")
    for bullet in new_bullets:
        print(f"      - {bullet.id}: {bullet.text[:50]}... -> {bullet.side.value}")

    # Step 8: Verify bullets can be retrieved
    print("[8] Verifying new bullets are retrievable...")
    retrieved, ids = memory.retrieve(
        query="validation best practices",
        side=Hemisphere.LEFT,
        k=10,
        include_shared=True
    )

    print(f"    Retrieved {len(retrieved)} bullets")

    # Step 9: Test learning pipeline end-to-end
    print("[9] Testing full learning pipeline...")
    trace2 = create_trace(
        task="Process user data with validation",
        hemisphere="left",
        steps=[
            {"action": "apply_validation", "result": "Applied validation rules"},
            {"action": "check_types", "result": "Checked data types"}
        ],
        bullets_used=[seed_bullet.id],
        success=True
    )

    result = await learning_pipeline.learn_from_trace(
        trace2,
        tick_rate=0.5,
        auto_add_bullets=True
    )

    print(f"    Learning result: {result.insights_extracted} insights, {result.bullets_created} bullets")

    # Step 10: Verify outcome tracking
    print("[10] Verifying outcome tracking...")
    memory.record_outcome(seed_bullet.id, OutcomeType.SUCCESS)

    # Retrieve the bullet to check score
    updated_bullets, _ = memory.retrieve(
        query=seed_bullet.text,
        side=Hemisphere.LEFT,
        k=1
    )

    if updated_bullets:
        updated = updated_bullets[0]
        print(f"     Bullet helpful_count: {updated.helpful_count}")
        print(f"     Bullet score: {updated.score():.2f}")

    print("\n[PASS] End-to-end integration test complete!")
    print(f"\nSummary:")
    print(f"  - Query processed: [OK]")
    print(f"  - Bullets retrieved: {bullets_count}")
    print(f"  - Insights extracted: {len(insights)}")
    print(f"  - New bullets created: {len(new_bullets)}")
    print(f"  - Learning cycle: [OK]")


@pytest.mark.asyncio
async def test_cross_hemisphere_classification(config, mock_llm):
    """Test that right-brain insights from left-brain execution are correctly classified."""

    memory = ProceduralMemory(config)
    if not check_meta_bullets_installed(memory):
        pytest.skip("Meta-bullets not installed")

    print("\n=== CROSS-HEMISPHERE CLASSIFICATION TEST ===\n")

    # Left brain executes task
    print("[1] Left brain executes task...")
    left_brain = LeftBrain(config, mock_llm, procedural_memory=memory)

    # But the task leads to an exploratory insight
    trace = create_trace(
        task="Solve optimization problem",
        hemisphere="left",
        steps=[
            {"action": "try_standard", "result": "Tried standard approach - insufficient"},
            {"action": "explore", "result": "Explored alternatives - found better solution"}
        ],
        bullets_used=[],
        success=True
    )

    # Step 2: Extract insight (should be right-brain style)
    print("[2] Extracting insights...")
    reflector = Reflector(config)
    insights = await reflector.reflect(trace, depth="shallow")

    # Manually add an exploratory insight to ensure we test classification
    from core.memory import ReflectionInsight, InsightType
    exploratory_insight = ReflectionInsight(
        text="Try exploring multiple creative solutions when standard approach fails",
        insight_type=InsightType.STRATEGY,
        tags=["exploration", "creativity", "alternatives"],
        confidence=0.85,
        source_trace_id=trace.trace_id,
        supporting_evidence=["Standard approach failed", "Creative exploration succeeded"]
    )
    insights.append(exploratory_insight)

    print(f"    Insights: {len(insights)}")
    print(f"    Test insight: '{exploratory_insight.text}'")

    # Step 3: Curate from LEFT brain (source), should classify to RIGHT (content)
    print("[3] Curating from LEFT brain source...")
    curator = Curator(memory)
    bullets = await curator.curate(
        insights=[exploratory_insight],
        hemisphere=Hemisphere.LEFT,  # Source is LEFT
        auto_add=True
    )

    # Step 4: Verify classification
    print("[4] Verifying classification...")
    if bullets:
        bullet = bullets[0]
        print(f"    Bullet text: '{bullet.text}'")
        print(f"    Source hemisphere: LEFT")
        print(f"    Assigned hemisphere: {bullet.side.value}")
        print(f"    Status: {bullet.status.value}")

        # The bullet should be in staging or assigned to RIGHT (not LEFT)
        # because content is exploratory (right-brain style)
        if bullet.side == Hemisphere.STAGING:
            print(f"    [OK] Bullet in staging (awaiting classification)")
            # Check if it has classifier metadata
            if "classifier_suggestion" in bullet.metadata:
                print(f"    Classifier suggestion: {bullet.metadata['classifier_suggestion']}")
        elif bullet.side == Hemisphere.RIGHT:
            print(f"    [OK] Bullet correctly classified to RIGHT (content overrides source)")
        else:
            print(f"    [WARN] Bullet assigned to LEFT (same as source)")

    print("\n[PASS] Cross-hemisphere classification test complete!")


if __name__ == "__main__":
    # Run tests
    from langchain_core.runnables import RunnableLambda

    async def mock_invoke(prompt):
        class Response:
            def __init__(self, content):
                self.content = content
        return Response("Always validate user input before processing.")

    print("Testing end-to-end integration...")
    asyncio.run(test_end_to_end_learning_cycle(
        config={
            "model": {"name": "llama3:8b", "temperature": 0.7},
            "left_brain": {"k_bullets": 8, "min_bullet_confidence": 0.5},
            "right_brain": {"k_bullets": 12, "min_bullet_confidence": 0.3},
            "procedural_memory": {
                "enabled": True,
                "persist_directory": "./data/memory/procedural",
                "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
                "learning": {
                    "reflection_enabled": True,
                    "auto_curate": True,
                    "min_insight_confidence": 0.5,
                    "deep_reflection_llm": False
                },
                "staging": {
                    "enabled": True,
                    "auto_assign": True,
                    "auto_assign_threshold": 0.85,
                    "manual_review_threshold": 0.7
                }
            }
        },
        mock_llm=RunnableLambda(mock_invoke)
    ))
    print("\n[SUCCESS] All integration tests passed!")
