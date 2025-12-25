"""Utility for formatting bullets for LLM prompts.

This module provides functions to format procedural memory bullets
into structured text that can be included in LLM context.
"""

from typing import List, Dict
from .bullet import Bullet, BulletType


def format_bullets_for_prompt(bullets: List[Bullet]) -> str:
    """
    Format bullets into structured text for LLM context.

    Groups bullets by type and formats them with clear headings
    for optimal LLM comprehension.

    Args:
        bullets: List of bullets to format

    Returns:
        Formatted string ready for inclusion in LLM prompt
    """
    if not bullets:
        return ""

    # Group bullets by type
    by_type: Dict[BulletType, List[Bullet]] = {}
    for bullet in bullets:
        if bullet.type not in by_type:
            by_type[bullet.type] = []
        by_type[bullet.type].append(bullet)

    # Build formatted output
    sections = []

    # Tool Rules (highest priority)
    if BulletType.TOOL_RULE in by_type:
        section = "TOOL RULES (API/Tool Usage):\n"
        for bullet in by_type[BulletType.TOOL_RULE]:
            section += f"  • {bullet.text}\n"
        sections.append(section)

    # Heuristics (general strategies)
    if BulletType.HEURISTIC in by_type:
        section = "BEST PRACTICES:\n"
        for bullet in by_type[BulletType.HEURISTIC]:
            section += f"  • {bullet.text}\n"
        sections.append(section)

    # Checklists (step-by-step)
    if BulletType.CHECKLIST in by_type:
        section = "PROCEDURES:\n"
        for bullet in by_type[BulletType.CHECKLIST]:
            section += f"  • {bullet.text}\n"
        sections.append(section)

    # Pitfalls (what to avoid)
    if BulletType.PITFALL in by_type:
        section = "COMMON PITFALLS (Avoid These):\n"
        for bullet in by_type[BulletType.PITFALL]:
            section += f"  ⚠ {bullet.text}\n"
        sections.append(section)

    # Patterns (recognized patterns)
    if BulletType.PATTERN in by_type:
        section = "KNOWN PATTERNS:\n"
        for bullet in by_type[BulletType.PATTERN]:
            section += f"  • {bullet.text}\n"
        sections.append(section)

    # Examples
    if BulletType.EXAMPLE in by_type:
        section = "EXAMPLES:\n"
        for bullet in by_type[BulletType.EXAMPLE]:
            section += f"  • {bullet.text}\n"
        sections.append(section)

    # Templates
    if BulletType.TEMPLATE in by_type:
        section = "TEMPLATES:\n"
        for bullet in by_type[BulletType.TEMPLATE]:
            section += f"  • {bullet.text}\n"
        sections.append(section)

    # Concepts
    if BulletType.CONCEPT in by_type:
        section = "KEY CONCEPTS:\n"
        for bullet in by_type[BulletType.CONCEPT]:
            section += f"  • {bullet.text}\n"
        sections.append(section)

    return "\n".join(sections)


def format_bullets_compact(bullets: List[Bullet], max_bullets: int = 10) -> str:
    """
    Format bullets in compact form (no grouping).

    Useful when you want a simple list without categorization.

    Args:
        bullets: List of bullets to format
        max_bullets: Maximum number of bullets to include

    Returns:
        Formatted string
    """
    if not bullets:
        return ""

    limited = bullets[:max_bullets]
    lines = []

    for i, bullet in enumerate(limited, 1):
        # Add emoji/marker based on type
        marker = _get_type_marker(bullet.type)
        lines.append(f"{i}. {marker} {bullet.text}")

    if len(bullets) > max_bullets:
        lines.append(f"   ... and {len(bullets) - max_bullets} more")

    return "\n".join(lines)


def format_bullets_with_metadata(bullets: List[Bullet]) -> str:
    """
    Format bullets with metadata (confidence, helpful/harmful counts).

    Useful for debugging or when the LLM needs to see bullet quality.

    Args:
        bullets: List of bullets to format

    Returns:
        Formatted string with metadata
    """
    if not bullets:
        return ""

    lines = []
    for bullet in bullets:
        score = bullet.score()
        conf = bullet.confidence
        lines.append(
            f"• {bullet.text}\n"
            f"  [Type: {bullet.type.value}, Score: {score:.2f}, "
            f"Confidence: {conf:.2f}, "
            f"Helpful: {bullet.helpful_count}, Harmful: {bullet.harmful_count}]"
        )

    return "\n".join(lines)


def _get_type_marker(bullet_type: BulletType) -> str:
    """Get emoji/marker for bullet type."""
    markers = {
        BulletType.TOOL_RULE: "🔧",
        BulletType.HEURISTIC: "💡",
        BulletType.CHECKLIST: "✓",
        BulletType.PITFALL: "⚠️",
        BulletType.PATTERN: "🔍",
        BulletType.EXAMPLE: "📝",
        BulletType.TEMPLATE: "📋",
        BulletType.CONCEPT: "🎯",
    }
    return markers.get(bullet_type, "•")


def extract_bullet_ids(bullets: List[Bullet]) -> List[str]:
    """
    Extract bullet IDs for outcome tracking.

    Args:
        bullets: List of bullets

    Returns:
        List of bullet IDs
    """
    return [bullet.id for bullet in bullets]
