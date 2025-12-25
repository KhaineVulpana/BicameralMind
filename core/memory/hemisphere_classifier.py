"""Hemisphere Classifier using meta-bullets for self-referential classification.

Instead of hard-coded rules, this classifier retrieves meta-bullets that
define what belongs in each hemisphere, then compares new insights against
those patterns.
"""

from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from loguru import logger

from .bullet import Bullet, BulletType, Hemisphere
from .procedural_memory import ProceduralMemory


@dataclass
class ClassificationResult:
    """Result of hemisphere classification."""
    hemisphere: Hemisphere
    confidence: float
    reasoning: str
    matched_patterns: List[str]  # IDs of meta-bullets that matched
    left_score: float
    right_score: float
    ambiguous: bool  # True if should go to human review


class HemisphereClassifier:
    """
    Classifies insights/bullets into hemispheres using meta-bullets.

    The classifier works by:
    1. Retrieving meta-bullets that define each hemisphere
    2. Comparing the candidate bullet against these patterns
    3. Scoring based on semantic similarity to meta-patterns
    4. Optionally using LLM for tie-breaking or low-confidence cases
    """

    def __init__(
        self,
        memory: ProceduralMemory,
        llm_client=None,
        use_llm_fallback: bool = True
    ):
        """
        Initialize classifier.

        Args:
            memory: ProceduralMemory instance with meta-bullets installed
            llm_client: Optional LLM for ambiguous cases
            use_llm_fallback: If True, use LLM when meta-bullet scoring is inconclusive
        """
        self.memory = memory
        self.llm = llm_client
        self.use_llm_fallback = use_llm_fallback

    async def classify(
        self,
        bullet_text: str,
        bullet_type: BulletType,
        source_hint: Hemisphere,
        tags: List[str]
    ) -> ClassificationResult:
        """
        Classify a bullet into left or right hemisphere.

        Args:
            bullet_text: The bullet text to classify
            bullet_type: The type of bullet
            source_hint: Which hemisphere executed the task (just a hint)
            tags: Associated tags

        Returns:
            ClassificationResult with hemisphere, confidence, and reasoning
        """
        logger.debug(f"Classifying bullet: '{bullet_text[:60]}...'")

        # Step 1: Retrieve meta-bullets for left hemisphere patterns
        left_patterns, left_ids = self.memory.retrieve(
            query=bullet_text,
            side=Hemisphere.LEFT,
            tags=["meta", "classification"],
            k=10,
            include_shared=False
        )

        # Filter to only meta-bullets
        left_patterns = [
            b for b in left_patterns
            if b.metadata.get("is_meta") and b.metadata.get("target_hemisphere") == "left"
        ]

        # Step 2: Retrieve meta-bullets for right hemisphere patterns
        right_patterns, right_ids = self.memory.retrieve(
            query=bullet_text,
            side=Hemisphere.RIGHT,
            tags=["meta", "classification"],
            k=10,
            include_shared=False
        )

        right_patterns = [
            b for b in right_patterns
            if b.metadata.get("is_meta") and b.metadata.get("target_hemisphere") == "right"
        ]

        # Step 3: Score based on pattern matches
        left_score = self._score_patterns(bullet_text, bullet_type, tags, left_patterns)
        right_score = self._score_patterns(bullet_text, bullet_type, tags, right_patterns)

        logger.debug(f"  Left score: {left_score:.2f}, Right score: {right_score:.2f}")

        # Step 4: Make decision
        result = self._make_decision(
            bullet_text=bullet_text,
            bullet_type=bullet_type,
            source_hint=source_hint,
            tags=tags,
            left_score=left_score,
            right_score=right_score,
            left_patterns=left_patterns,
            right_patterns=right_patterns
        )

        # Step 5: LLM fallback for ambiguous cases
        if result.ambiguous and self.use_llm_fallback and self.llm:
            logger.debug("  Ambiguous - using LLM fallback")
            result = await self._llm_classify(
                bullet_text, bullet_type, source_hint, tags,
                left_score, right_score, left_patterns, right_patterns
            )

        logger.info(
            f"  ✓ Classified as {result.hemisphere.value.upper()} "
            f"(confidence: {result.confidence:.2f})"
        )

        return result

    def _score_patterns(
        self,
        bullet_text: str,
        bullet_type: BulletType,
        tags: List[str],
        patterns: List[Bullet]
    ) -> float:
        """
        Score how well the bullet matches a set of meta-patterns.

        Uses multiple signals:
        - Semantic similarity (from vector retrieval)
        - Keyword matching
        - Tag overlap
        - Bullet type alignment

        Returns:
            Score from 0.0 to 1.0
        """
        if not patterns:
            return 0.0

        text_lower = bullet_text.lower()
        score = 0.0
        matches = 0

        for pattern in patterns:
            pattern_score = 0.0

            # Signal 1: Vector similarity (patterns are already retrieved via similarity)
            # Top results have higher implicit similarity
            # Give diminishing weight: 1st = 1.0, 2nd = 0.9, 3rd = 0.8, etc.
            rank_bonus = max(0.5, 1.0 - (matches * 0.1))
            pattern_score += rank_bonus * 0.4  # 40% weight to retrieval rank

            # Signal 2: Keyword matching from meta-bullet text
            keywords = self._extract_keywords(pattern.text)
            keyword_matches = sum(1 for kw in keywords if kw in text_lower)
            if keywords:
                keyword_ratio = keyword_matches / len(keywords)
                pattern_score += keyword_ratio * 0.3  # 30% weight

            # Signal 3: Tag overlap
            if pattern.tags and tags:
                tag_overlap = len(set(pattern.tags) & set(tags)) / len(set(pattern.tags) | set(tags))
                pattern_score += tag_overlap * 0.2  # 20% weight

            # Signal 4: Bullet type alignment
            # Some types naturally align with hemispheres
            type_alignment = self._get_type_alignment(bullet_type, pattern)
            pattern_score += type_alignment * 0.1  # 10% weight

            score += pattern_score
            matches += 1

        # Normalize by number of patterns
        return min(1.0, score / max(1, len(patterns)))

    def _extract_keywords(self, meta_bullet_text: str) -> List[str]:
        """
        Extract classification keywords from meta-bullet text.

        Example:
        "Does your statement use absolute language? (always, never, must) → LEFT"
        Returns: ["always", "never", "must", "absolute", "language"]
        """
        # Remove meta-syntax
        text = meta_bullet_text.lower()
        text = text.replace("→ left", "").replace("→ right", "")
        text = text.replace("does your", "").replace("?", "")

        # Extract keywords from parentheses
        keywords = []
        if "(" in text and ")" in text:
            paren_content = text[text.index("(") + 1:text.index(")")]
            keywords.extend(paren_content.replace(",", " ").split())

        # Extract key terms
        key_terms = ["always", "never", "must", "ensure", "require", "validate",
                     "try", "explore", "consider", "maybe", "what if", "alternative",
                     "binary", "yes/no", "check", "verify", "edge case", "anomaly"]

        for term in key_terms:
            if term in text:
                keywords.append(term)

        return [kw.strip() for kw in keywords if len(kw.strip()) > 2]

    def _get_type_alignment(self, bullet_type: BulletType, pattern: Bullet) -> float:
        """
        Check if bullet type naturally aligns with hemisphere.

        Some bullet types tend toward left or right:
        - CHECKLIST, TOOL_RULE → Left (precise, procedural)
        - PATTERN, CONCEPT → Right (exploratory, abstract)
        - HEURISTIC, PITFALL → Either (depends on content)
        """
        left_types = {BulletType.CHECKLIST, BulletType.TOOL_RULE}
        right_types = {BulletType.PATTERN, BulletType.CONCEPT}

        target = pattern.metadata.get("target_hemisphere")

        if bullet_type in left_types and target == "left":
            return 1.0
        elif bullet_type in right_types and target == "right":
            return 1.0
        else:
            return 0.5  # Neutral

    def _make_decision(
        self,
        bullet_text: str,
        bullet_type: BulletType,
        source_hint: Hemisphere,
        tags: List[str],
        left_score: float,
        right_score: float,
        left_patterns: List[Bullet],
        right_patterns: List[Bullet]
    ) -> ClassificationResult:
        """
        Make final classification decision based on scores.

        Decision rules:
        1. If one side >> other (>0.3 difference), choose it
        2. If both low (<0.4), ambiguous
        3. If close (difference <0.2), ambiguous
        4. Otherwise, choose higher score
        """
        diff = abs(left_score - right_score)

        # Clear winner
        if diff > 0.3:
            if left_score > right_score:
                hemisphere = Hemisphere.LEFT
                confidence = min(0.95, 0.6 + left_score * 0.4)
                matched = [p.id for p in left_patterns[:3]]
                reasoning = f"Strong left pattern match (score: {left_score:.2f} vs {right_score:.2f})"
                ambiguous = False
            else:
                hemisphere = Hemisphere.RIGHT
                confidence = min(0.95, 0.6 + right_score * 0.4)
                matched = [p.id for p in right_patterns[:3]]
                reasoning = f"Strong right pattern match (score: {right_score:.2f} vs {left_score:.2f})"
                ambiguous = False

        # Both scores low - no clear pattern
        elif left_score < 0.4 and right_score < 0.4:
            # Fallback to source hint
            hemisphere = source_hint
            confidence = 0.5
            matched = []
            reasoning = f"No clear pattern match - defaulting to source hemisphere ({source_hint.value})"
            ambiguous = True

        # Scores close - ambiguous
        elif diff < 0.2:
            # Use source hint as tie-breaker
            hemisphere = source_hint
            confidence = 0.6
            matched = []
            reasoning = f"Ambiguous classification (scores: L={left_score:.2f}, R={right_score:.2f}) - using source hint"
            ambiguous = True

        # Modest preference
        else:
            if left_score > right_score:
                hemisphere = Hemisphere.LEFT
                confidence = min(0.85, 0.5 + left_score * 0.35)
                matched = [p.id for p in left_patterns[:2]]
                reasoning = f"Moderate left preference (score: {left_score:.2f} vs {right_score:.2f})"
                ambiguous = False
            else:
                hemisphere = Hemisphere.RIGHT
                confidence = min(0.85, 0.5 + right_score * 0.35)
                matched = [p.id for p in right_patterns[:2]]
                reasoning = f"Moderate right preference (score: {right_score:.2f} vs {left_score:.2f})"
                ambiguous = False

        return ClassificationResult(
            hemisphere=hemisphere,
            confidence=confidence,
            reasoning=reasoning,
            matched_patterns=matched,
            left_score=left_score,
            right_score=right_score,
            ambiguous=ambiguous
        )

    async def _llm_classify(
        self,
        bullet_text: str,
        bullet_type: BulletType,
        source_hint: Hemisphere,
        tags: List[str],
        left_score: float,
        right_score: float,
        left_patterns: List[Bullet],
        right_patterns: List[Bullet]
    ) -> ClassificationResult:
        """
        Use LLM to classify ambiguous cases.

        The LLM sees:
        - The bullet text
        - Matched meta-patterns from both sides
        - Current scores
        - Source hint
        """
        # Format meta-patterns for LLM
        left_examples = "\n".join([f"  - {p.text}" for p in left_patterns[:3]])
        right_examples = "\n".join([f"  - {p.text}" for p in right_patterns[:3]])

        prompt = f"""You are classifying a procedural memory bullet into LEFT or RIGHT hemisphere.

BULLET TO CLASSIFY:
Text: "{bullet_text}"
Type: {bullet_type.value}
Tags: {", ".join(tags)}
Source: {source_hint.value} brain executed the task that generated this

META-PATTERN MATCHING RESULTS:
Left hemisphere patterns (score: {left_score:.2f}):
{left_examples if left_examples else "  (no strong matches)"}

Right hemisphere patterns (score: {right_score:.2f}):
{right_examples if right_examples else "  (no strong matches)"}

LEFT HEMISPHERE (Pattern Continuity):
- Confirmatory, absolute language (always, never, must)
- Binary decisions, validation, verification
- Precise rules, required fields, schemas
- Step-by-step procedures
- Specific error prevention

RIGHT HEMISPHERE (Pattern Violation):
- Exploratory language (try, consider, maybe)
- Alternatives, variations, reframings
- Assumption-challenging, open questions
- Edge cases, anomalies, pattern violations
- Novelty-seeking, creativity

Based on the bullet's COGNITIVE STYLE (not just execution context), classify it:

HEMISPHERE: left | right
CONFIDENCE: 0.0-1.0
REASONING: One sentence explaining why
"""

        try:
            response = await self.llm.ainvoke(prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)

            # Parse response
            hemisphere, confidence, reasoning = self._parse_llm_response(response_text)

            return ClassificationResult(
                hemisphere=hemisphere,
                confidence=confidence,
                reasoning=f"LLM classification: {reasoning}",
                matched_patterns=[],
                left_score=left_score,
                right_score=right_score,
                ambiguous=False
            )

        except Exception as e:
            logger.error(f"LLM classification failed: {e}")

            # Fallback to source hint
            return ClassificationResult(
                hemisphere=source_hint,
                confidence=0.5,
                reasoning=f"LLM classification failed - using source hint",
                matched_patterns=[],
                left_score=left_score,
                right_score=right_score,
                ambiguous=True
            )

    def _parse_llm_response(self, text: str) -> Tuple[Hemisphere, float, str]:
        """Parse LLM classification response."""
        lines = text.strip().split('\n')

        hemisphere = Hemisphere.LEFT
        confidence = 0.5
        reasoning = ""

        for line in lines:
            if "HEMISPHERE:" in line:
                val = line.split(":", 1)[1].strip().lower()
                hemisphere = Hemisphere.LEFT if "left" in val else Hemisphere.RIGHT
            elif "CONFIDENCE:" in line:
                try:
                    confidence = float(line.split(":", 1)[1].strip())
                except:
                    confidence = 0.5
            elif "REASONING:" in line:
                reasoning = line.split(":", 1)[1].strip()

        return (hemisphere, confidence, reasoning)
