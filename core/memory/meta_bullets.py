"""Meta-bullets that define hemisphere characteristics.

These bullets act as self-referential classification rules:
they describe what kinds of knowledge belong in each hemisphere.
"""

from typing import List
from .bullet import Bullet, BulletType, BulletStatus, Hemisphere


def get_meta_bullets() -> List[Bullet]:
    """
    Get base set of meta-bullets that define hemisphere cognitive styles.

    These are installed at system initialization and stored in a special
    'procedural_meta' collection. They are used by the HemisphereClassifier
    to determine where new bullets should be assigned.

    Returns:
        List of meta-bullets (both left and right hemisphere definitions)
    """
    meta_bullets = []

    # ============================================================================
    # LEFT HEMISPHERE META-BULLETS
    # Define what belongs in left brain (pattern continuity)
    # ============================================================================


    meta_bullets.append(Bullet(
        id="meta_left_009",
        text="Does the insight confirm a known pattern or rule? -> LEFT brain",
        side=Hemisphere.LEFT,
        type=BulletType.HEURISTIC,
        tags=["meta", "classification", "pattern_recognition"],
        confidence=1.0,
        helpful_count=100,
        harmful_count=0,
        status=BulletStatus.ACTIVE,
        metadata={"is_meta": True, "target_hemisphere": "left"}
    ))

    meta_bullets.append(Bullet(
        id="meta_left_010",
        text="Does the insight replicate a proven pattern or procedure? -> LEFT brain",
        side=Hemisphere.LEFT,
        type=BulletType.HEURISTIC,
        tags=["meta", "classification", "pattern_replication"],
        confidence=1.0,
        helpful_count=100,
        harmful_count=0,
        status=BulletStatus.ACTIVE,
        metadata={"is_meta": True, "target_hemisphere": "left"}
    ))

    meta_bullets.append(Bullet(
        id="meta_left_011",
        text="Is the reasoning logic-based or constraint-driven? -> LEFT brain",
        side=Hemisphere.LEFT,
        type=BulletType.HEURISTIC,
        tags=["meta", "classification", "logic"],
        confidence=1.0,
        helpful_count=100,
        harmful_count=0,
        status=BulletStatus.ACTIVE,
        metadata={"is_meta": True, "target_hemisphere": "left"}
    ))

    # Language patterns
    meta_bullets.append(Bullet(
        id="meta_left_001",
        text="Does your statement use absolute language? (always, never, must, ensure, require) -> LEFT brain",
        side=Hemisphere.LEFT,
        type=BulletType.HEURISTIC,
        tags=["meta", "classification", "language", "absolute"],
        confidence=1.0,
        helpful_count=100,  # Pre-validated
        harmful_count=0,
        status=BulletStatus.ACTIVE,
        metadata={"is_meta": True, "target_hemisphere": "left"}
    ))

    meta_bullets.append(Bullet(
        id="meta_left_002",
        text="Does your statement describe a validation or verification step? (check, validate, verify, confirm) -> LEFT brain",
        side=Hemisphere.LEFT,
        type=BulletType.HEURISTIC,
        tags=["meta", "classification", "validation"],
        confidence=1.0,
        helpful_count=100,
        status=BulletStatus.ACTIVE,
        metadata={"is_meta": True, "target_hemisphere": "left"}
    ))

    meta_bullets.append(Bullet(
        id="meta_left_003",
        text="Does your rule specify required fields or constraints? (required, mandatory, must have) -> LEFT brain",
        side=Hemisphere.LEFT,
        type=BulletType.HEURISTIC,
        tags=["meta", "classification", "constraints"],
        confidence=1.0,
        helpful_count=100,
        status=BulletStatus.ACTIVE,
        metadata={"is_meta": True, "target_hemisphere": "left"}
    ))

    # Question patterns
    meta_bullets.append(Bullet(
        id="meta_left_004",
        text="Does your question have a binary answer? (yes/no, true/false, pass/fail) -> LEFT brain",
        side=Hemisphere.LEFT,
        type=BulletType.HEURISTIC,
        tags=["meta", "classification", "questions", "binary"],
        confidence=1.0,
        helpful_count=100,
        status=BulletStatus.ACTIVE,
        metadata={"is_meta": True, "target_hemisphere": "left"}
    ))

    meta_bullets.append(Bullet(
        id="meta_left_005",
        text="Does your question request a specific choice from defined options? (which of A/B/C, select from) -> LEFT brain",
        side=Hemisphere.LEFT,
        type=BulletType.HEURISTIC,
        tags=["meta", "classification", "questions", "multiple_choice"],
        confidence=1.0,
        helpful_count=100,
        status=BulletStatus.ACTIVE,
        metadata={"is_meta": True, "target_hemisphere": "left"}
    ))

    # Procedural patterns
    meta_bullets.append(Bullet(
        id="meta_left_006",
        text="Does your bullet describe a step-by-step procedure or checklist? -> LEFT brain",
        side=Hemisphere.LEFT,
        type=BulletType.HEURISTIC,
        tags=["meta", "classification", "procedures"],
        confidence=1.0,
        helpful_count=100,
        status=BulletStatus.ACTIVE,
        metadata={"is_meta": True, "target_hemisphere": "left"}
    ))

    meta_bullets.append(Bullet(
        id="meta_left_007",
        text="Does your rule specify exact format or schema requirements? -> LEFT brain",
        side=Hemisphere.LEFT,
        type=BulletType.HEURISTIC,
        tags=["meta", "classification", "schema", "format"],
        confidence=1.0,
        helpful_count=100,
        status=BulletStatus.ACTIVE,
        metadata={"is_meta": True, "target_hemisphere": "left"}
    ))

    # Risk/error patterns
    meta_bullets.append(Bullet(
        id="meta_left_008",
        text="Does your bullet warn about specific errors or known pitfalls? (avoid X, prevent Y, watch for Z) -> LEFT brain",
        side=Hemisphere.LEFT,
        type=BulletType.HEURISTIC,
        tags=["meta", "classification", "pitfalls", "errors"],
        confidence=1.0,
        helpful_count=100,
        status=BulletStatus.ACTIVE,
        metadata={"is_meta": True, "target_hemisphere": "left"}
    ))

    # ============================================================================
    # RIGHT HEMISPHERE META-BULLETS
    # Define what belongs in right brain (pattern violation/exploration)
    # ============================================================================


    meta_bullets.append(Bullet(
        id="meta_right_010",
        text="Does the insight recognize a pattern break or contradiction? -> RIGHT brain",
        side=Hemisphere.RIGHT,
        type=BulletType.HEURISTIC,
        tags=["meta", "classification", "pattern_disruption"],
        confidence=1.0,
        helpful_count=100,
        harmful_count=0,
        status=BulletStatus.ACTIVE,
        metadata={"is_meta": True, "target_hemisphere": "right"}
    ))

    meta_bullets.append(Bullet(
        id="meta_right_011",
        text="Does the insight mutate a pattern or suggest novel variation? -> RIGHT brain",
        side=Hemisphere.RIGHT,
        type=BulletType.HEURISTIC,
        tags=["meta", "classification", "pattern_mutation"],
        confidence=1.0,
        helpful_count=100,
        harmful_count=0,
        status=BulletStatus.ACTIVE,
        metadata={"is_meta": True, "target_hemisphere": "right"}
    ))

    meta_bullets.append(Bullet(
        id="meta_right_012",
        text="Is the insight abstract, conceptual, or analogy-based? -> RIGHT brain",
        side=Hemisphere.RIGHT,
        type=BulletType.HEURISTIC,
        tags=["meta", "classification", "abstract"],
        confidence=1.0,
        helpful_count=100,
        harmful_count=0,
        status=BulletStatus.ACTIVE,
        metadata={"is_meta": True, "target_hemisphere": "right"}
    ))

    # Language patterns
    meta_bullets.append(Bullet(
        id="meta_right_001",
        text="Does your statement use exploratory language? (try, consider, explore, experiment, maybe) -> RIGHT brain",
        side=Hemisphere.RIGHT,
        type=BulletType.HEURISTIC,
        tags=["meta", "classification", "language", "exploratory"],
        confidence=1.0,
        helpful_count=100,
        status=BulletStatus.ACTIVE,
        metadata={"is_meta": True, "target_hemisphere": "right"}
    ))

    meta_bullets.append(Bullet(
        id="meta_right_002",
        text="Does your statement suggest alternatives or variations? (alternative, variant, different approach, another way) -> RIGHT brain",
        side=Hemisphere.RIGHT,
        type=BulletType.HEURISTIC,
        tags=["meta", "classification", "alternatives"],
        confidence=1.0,
        helpful_count=100,
        status=BulletStatus.ACTIVE,
        metadata={"is_meta": True, "target_hemisphere": "right"}
    ))

    meta_bullets.append(Bullet(
        id="meta_right_003",
        text="Does your statement challenge assumptions? (what if, question whether, assume, reconsider) -> RIGHT brain",
        side=Hemisphere.RIGHT,
        type=BulletType.HEURISTIC,
        tags=["meta", "classification", "assumptions"],
        confidence=1.0,
        helpful_count=100,
        status=BulletStatus.ACTIVE,
        metadata={"is_meta": True, "target_hemisphere": "right"}
    ))

    # Question patterns
    meta_bullets.append(Bullet(
        id="meta_right_004",
        text="Does your question ask 'why' or request explanation? (why, how come, what causes) -> RIGHT brain",
        side=Hemisphere.RIGHT,
        type=BulletType.HEURISTIC,
        tags=["meta", "classification", "questions", "why"],
        confidence=1.0,
        helpful_count=100,
        status=BulletStatus.ACTIVE,
        metadata={"is_meta": True, "target_hemisphere": "right"}
    ))

    meta_bullets.append(Bullet(
        id="meta_right_005",
        text="Does your question expand possibility space? (what else, what other, what if we, could we) -> RIGHT brain",
        side=Hemisphere.RIGHT,
        type=BulletType.HEURISTIC,
        tags=["meta", "classification", "questions", "possibility"],
        confidence=1.0,
        helpful_count=100,
        status=BulletStatus.ACTIVE,
        metadata={"is_meta": True, "target_hemisphere": "right"}
    ))

    # Pattern patterns
    meta_bullets.append(Bullet(
        id="meta_right_006",
        text="Does your insight describe a pattern violation or anomaly? (breaks pattern, unexpected, contradicts, anomaly) -> RIGHT brain",
        side=Hemisphere.RIGHT,
        type=BulletType.HEURISTIC,
        tags=["meta", "classification", "anomaly", "violation"],
        confidence=1.0,
        helpful_count=100,
        status=BulletStatus.ACTIVE,
        metadata={"is_meta": True, "target_hemisphere": "right"}
    ))

    meta_bullets.append(Bullet(
        id="meta_right_007",
        text="Does your bullet describe edge cases or boundary conditions? (edge case, corner case, unusual scenario) -> RIGHT brain",
        side=Hemisphere.RIGHT,
        type=BulletType.HEURISTIC,
        tags=["meta", "classification", "edge_cases"],
        confidence=1.0,
        helpful_count=100,
        status=BulletStatus.ACTIVE,
        metadata={"is_meta": True, "target_hemisphere": "right"}
    ))

    # Novelty patterns
    meta_bullets.append(Bullet(
        id="meta_right_008",
        text="Does your strategy suggest creative reframing or recombination? (reframe as, combine, remix, analogous to) -> RIGHT brain",
        side=Hemisphere.RIGHT,
        type=BulletType.HEURISTIC,
        tags=["meta", "classification", "creativity", "reframing"],
        confidence=1.0,
        helpful_count=100,
        status=BulletStatus.ACTIVE,
        metadata={"is_meta": True, "target_hemisphere": "right"}
    ))

    meta_bullets.append(Bullet(
        id="meta_right_009",
        text="Does your insight describe novelty-seeking behavior? (novel approach, unconventional, break from tradition) -> RIGHT brain",
        side=Hemisphere.RIGHT,
        type=BulletType.HEURISTIC,
        tags=["meta", "classification", "novelty"],
        confidence=1.0,
        helpful_count=100,
        status=BulletStatus.ACTIVE,
        metadata={"is_meta": True, "target_hemisphere": "right"}
    ))

    # ============================================================================
    # AMBIGUOUS CASE HANDLERS
    # When meta-bullets conflict or don't match well
    # ============================================================================

    meta_bullets.append(Bullet(
        id="meta_ambiguous_001",
        text="If bullet matches both left AND right patterns, flag for human review",
        side=Hemisphere.LEFT,  # Meta-organizational
        type=BulletType.HEURISTIC,
        tags=["meta", "classification", "ambiguous"],
        confidence=1.0,
        helpful_count=100,
        status=BulletStatus.ACTIVE,
        metadata={"is_meta": True, "target_hemisphere": "review"}
    ))

    meta_bullets.append(Bullet(
        id="meta_ambiguous_002",
        text="If bullet matches NO meta-patterns strongly (all scores < 0.5), flag for human review",
        side=Hemisphere.LEFT,
        type=BulletType.HEURISTIC,
        tags=["meta", "classification", "uncertain"],
        confidence=1.0,
        helpful_count=100,
        status=BulletStatus.ACTIVE,
        metadata={"is_meta": True, "target_hemisphere": "review"}
    ))

    return meta_bullets


def install_meta_bullets(memory):
    """
    Install meta-bullets into procedural memory.

    This should be called once during system initialization.
    Meta-bullets are stored in the regular collections but marked
    with metadata={"is_meta": True} for identification.

    Args:
        memory: ProceduralMemory instance
    """
    from loguru import logger

    meta_bullets = get_meta_bullets()

    logger.info(f"Installing {len(meta_bullets)} meta-bullets...")

    for bullet in meta_bullets:
        # Add to appropriate hemisphere
        memory.store.add_bullet(
            side=bullet.side.value,
            text=bullet.text,
            bullet_type=bullet.type.value,
            tags=bullet.tags,
            status=bullet.status.value,
            confidence=bullet.confidence,
            metadata=bullet.metadata,
            bullet_id=bullet.id
        )

    logger.success(f"OK Installed {len(meta_bullets)} meta-bullets for hemisphere classification")

    # Return counts by hemisphere
    left_count = sum(1 for b in meta_bullets if b.side == Hemisphere.LEFT and b.metadata.get("target_hemisphere") == "left")
    right_count = sum(1 for b in meta_bullets if b.side == Hemisphere.RIGHT and b.metadata.get("target_hemisphere") == "right")

    return {
        "total": len(meta_bullets),
        "left_patterns": left_count,
        "right_patterns": right_count,
        "ambiguous_handlers": 2
    }


def check_meta_bullets_installed(memory) -> bool:
    """
    Check if meta-bullets are already installed.

    Returns:
        True if meta-bullets exist, False otherwise
    """
    # Try to retrieve a known meta-bullet
    bullets, _ = memory.retrieve(
        query="Does your question have binary answer",
        side=Hemisphere.LEFT,
        k=1,
        include_shared=False
    )

    if bullets and bullets[0].metadata.get("is_meta"):
        return True

    return False
