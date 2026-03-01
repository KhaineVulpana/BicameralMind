"""Install question template bullets for agent question-asking.

This script installs predefined question bullets that guide agents on
when and how to ask questions for clarification or exploration.

Left brain: Binary/categorical questions for disambiguation
Right brain: Open-ended/exploratory questions for possibility expansion
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml
from loguru import logger
from core.memory import ProceduralMemory, Hemisphere, BulletType, BulletStatus


def get_question_bullets():
    """Get predefined question template bullets."""
    question_bullets = []

    # ============================================================================
    # LEFT BRAIN QUESTIONS (Binary, Categorical, Clarifying)
    # ============================================================================

    question_bullets.append({
        "text": "When requirements are ambiguous, ask: 'Should this be X or Y?' to get binary clarification",
        "side": Hemisphere.LEFT,
        "type": BulletType.QUESTION,
        "tags": ["questions", "clarification", "binary"],
        "confidence": 0.9,
        "status": BulletStatus.ACTIVE,
        "metadata": {"category": "disambiguation", "question_style": "binary"}
    })

    question_bullets.append({
        "text": "If input format is unclear, ask: 'Is the input format A, B, or C?' to establish constraints",
        "side": Hemisphere.LEFT,
        "type": BulletType.QUESTION,
        "tags": ["questions", "format", "constraints"],
        "confidence": 0.9,
        "status": BulletStatus.ACTIVE,
        "metadata": {"category": "format_clarification", "question_style": "multiple_choice"}
    })

    question_bullets.append({
        "text": "When validation rules are unspecified, ask: 'What are the required fields?' to define schema",
        "side": Hemisphere.LEFT,
        "type": BulletType.QUESTION,
        "tags": ["questions", "validation", "schema"],
        "confidence": 0.85,
        "status": BulletStatus.ACTIVE,
        "metadata": {"category": "schema_definition", "question_style": "specific"}
    })

    question_bullets.append({
        "text": "If error handling is ambiguous, ask: 'Should errors be logged, raised, or silently handled?' for clear policy",
        "side": Hemisphere.LEFT,
        "type": BulletType.QUESTION,
        "tags": ["questions", "errors", "policy"],
        "confidence": 0.85,
        "status": BulletStatus.ACTIVE,
        "metadata": {"category": "error_policy", "question_style": "categorical"}
    })

    question_bullets.append({
        "text": "When edge cases appear, ask: 'How should the system behave when X occurs?' to establish rules",
        "side": Hemisphere.LEFT,
        "type": BulletType.QUESTION,
        "tags": ["questions", "edge_cases", "behavior"],
        "confidence": 0.80,
        "status": BulletStatus.ACTIVE,
        "metadata": {"category": "edge_case_handling", "question_style": "specific"}
    })

    question_bullets.append({
        "text": "If performance requirements are missing, ask: 'What are the acceptable latency/throughput thresholds?' for benchmarks",
        "side": Hemisphere.LEFT,
        "type": BulletType.QUESTION,
        "tags": ["questions", "performance", "requirements"],
        "confidence": 0.75,
        "status": BulletStatus.ACTIVE,
        "metadata": {"category": "performance_specs", "question_style": "quantitative"}
    })

    # ============================================================================
    # RIGHT BRAIN QUESTIONS (Open-ended, Exploratory, Why-focused)
    # ============================================================================

    question_bullets.append({
        "text": "When exploring alternatives, ask: 'What other approaches might work here?' to expand solution space",
        "side": Hemisphere.RIGHT,
        "type": BulletType.QUESTION,
        "tags": ["questions", "exploration", "alternatives"],
        "confidence": 0.9,
        "status": BulletStatus.ACTIVE,
        "metadata": {"category": "alternative_exploration", "question_style": "open_ended"}
    })

    question_bullets.append({
        "text": "If constraints seem arbitrary, ask: 'Why is this constraint necessary?' to understand deeper reasoning",
        "side": Hemisphere.RIGHT,
        "type": BulletType.QUESTION,
        "tags": ["questions", "constraints", "reasoning"],
        "confidence": 0.85,
        "status": BulletStatus.ACTIVE,
        "metadata": {"category": "constraint_analysis", "question_style": "why"}
    })

    question_bullets.append({
        "text": "When standard patterns fail, ask: 'What if we tried approaching this from a completely different angle?' for reframing",
        "side": Hemisphere.RIGHT,
        "type": BulletType.QUESTION,
        "tags": ["questions", "reframing", "creativity"],
        "confidence": 0.80,
        "status": BulletStatus.ACTIVE,
        "metadata": {"category": "creative_reframing", "question_style": "what_if"}
    })

    question_bullets.append({
        "text": "If assumptions are unclear, ask: 'What assumptions are we making that might not be true?' to challenge thinking",
        "side": Hemisphere.RIGHT,
        "type": BulletType.QUESTION,
        "tags": ["questions", "assumptions", "critical_thinking"],
        "confidence": 0.85,
        "status": BulletStatus.ACTIVE,
        "metadata": {"category": "assumption_challenge", "question_style": "reflective"}
    })

    question_bullets.append({
        "text": "When exploring edge cases, ask: 'What unusual scenarios might we encounter in practice?' for boundary discovery",
        "side": Hemisphere.RIGHT,
        "type": BulletType.QUESTION,
        "tags": ["questions", "edge_cases", "exploration"],
        "confidence": 0.75,
        "status": BulletStatus.ACTIVE,
        "metadata": {"category": "edge_case_discovery", "question_style": "exploratory"}
    })

    question_bullets.append({
        "text": "If user intent is ambiguous, ask: 'What is the underlying goal you're trying to achieve?' to understand deeper needs",
        "side": Hemisphere.RIGHT,
        "type": BulletType.QUESTION,
        "tags": ["questions", "intent", "needs"],
        "confidence": 0.90,
        "status": BulletStatus.ACTIVE,
        "metadata": {"category": "intent_discovery", "question_style": "goal_focused"}
    })

    question_bullets.append({
        "text": "When encountering novel situations, ask: 'How is this similar to problems we've solved before?' for pattern transfer",
        "side": Hemisphere.RIGHT,
        "type": BulletType.QUESTION,
        "tags": ["questions", "analogies", "pattern_transfer"],
        "confidence": 0.80,
        "status": BulletStatus.ACTIVE,
        "metadata": {"category": "analogy_seeking", "question_style": "comparative"}
    })

    # ============================================================================
    # META-QUESTIONS (When to ask questions)
    # ============================================================================

    question_bullets.append({
        "text": "Ask questions when confidence in understanding is below 0.7",
        "side": Hemisphere.LEFT,
        "type": BulletType.HEURISTIC,
        "tags": ["questions", "meta", "confidence"],
        "confidence": 0.85,
        "status": BulletStatus.ACTIVE,
        "metadata": {"category": "questioning_heuristic", "trigger": "low_confidence"}
    })

    question_bullets.append({
        "text": "Ask questions before making irreversible decisions or changes",
        "side": Hemisphere.LEFT,
        "type": BulletType.HEURISTIC,
        "tags": ["questions", "meta", "decisions"],
        "confidence": 0.90,
        "status": BulletStatus.ACTIVE,
        "metadata": {"category": "questioning_heuristic", "trigger": "irreversible_action"}
    })

    question_bullets.append({
        "text": "Ask exploratory questions when novelty score is high (>0.7) to understand new patterns",
        "side": Hemisphere.RIGHT,
        "type": BulletType.HEURISTIC,
        "tags": ["questions", "meta", "novelty"],
        "confidence": 0.80,
        "status": BulletStatus.ACTIVE,
        "metadata": {"category": "questioning_heuristic", "trigger": "high_novelty"}
    })

    return question_bullets


def install_question_bullets(memory: ProceduralMemory):
    """Install question bullets into procedural memory."""

    bullets = get_question_bullets()

    logger.info(f"Installing {len(bullets)} question template bullets...")

    left_count = 0
    right_count = 0
    meta_count = 0

    for bullet_data in bullets:
        bullet = memory.add(
            text=bullet_data["text"],
            side=bullet_data["side"],
            bullet_type=bullet_data["type"],
            tags=bullet_data["tags"],
            confidence=bullet_data["confidence"],
            status=bullet_data["status"],
            metadata=bullet_data["metadata"]
        )

        if bullet_data["side"] == Hemisphere.LEFT:
            if bullet_data["type"] == BulletType.QUESTION:
                left_count += 1
            else:
                meta_count += 1
        else:
            if bullet_data["type"] == BulletType.QUESTION:
                right_count += 1
            else:
                meta_count += 1

    logger.success(f"Installed {len(bullets)} question bullets:")
    logger.info(f"  Left brain questions: {left_count}")
    logger.info(f"  Right brain questions: {right_count}")
    logger.info(f"  Meta-questioning heuristics: {meta_count}")

    return {
        "total": len(bullets),
        "left_questions": left_count,
        "right_questions": right_count,
        "meta_heuristics": meta_count
    }


def main():
    """Install question bullets to procedural memory."""

    # Load config
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    logger.info("Initializing procedural memory...")
    memory = ProceduralMemory(config)

    # Install question bullets
    logger.info("Installing question template bullets...")
    result = install_question_bullets(memory)

    # Report results
    logger.success(f"Installation complete!")
    logger.info(f"  Total bullets: {result['total']}")
    logger.info(f"  Left brain questions: {result['left_questions']}")
    logger.info(f"  Right brain questions: {result['right_questions']}")
    logger.info(f"  Meta-questioning heuristics: {result['meta_heuristics']}")

    logger.info("\nQuestion bullets are now available for agent retrieval!")
    logger.info("Agents will use these templates to know when and how to ask questions.")


if __name__ == "__main__":
    main()
