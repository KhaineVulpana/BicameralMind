"""Right Brain: Pattern Violation and Mutation"""
from core.base_agent import BrainAgent, Message, MessageType
from core.memory import ProceduralMemory, Hemisphere
from core.memory.bullet_formatter import format_bullets_for_prompt
from typing import Dict, Any, List, Optional
import asyncio
from langchain_core.prompts import ChatPromptTemplate


class RightBrain(BrainAgent):
    """
    Right Brain Agent: Pattern Breaking & Mutation
    - Detects pattern violations and anomalies
    - Notices when expectations fail
    - Mutates patterns and creates variants
    - Explores novel combinations
    - Generates open-ended possibilities
    """

    def __init__(
        self,
        config: Dict[str, Any],
        llm_client,
        procedural_memory: Optional[ProceduralMemory] = None
    ):
        super().__init__("RightBrain", config.get("right_brain", {}))
        self.llm = llm_client
        self.memory = procedural_memory

        # Configuration for bullet retrieval (right brain retrieves more, lower confidence threshold)
        self.k_bullets = config.get("right_brain", {}).get("k_bullets", 12)
        self.min_confidence = config.get("right_brain", {}).get("min_bullet_confidence", 0.3)

        self.exploration_template = ChatPromptTemplate.from_messages([
            ("system", """You are the RIGHT HEMISPHERE of a bicameral mind.
Your role: PATTERN BREAKING and MUTATION.

Core behaviors:
1. Detect anomalies and pattern violations
2. Notice when expected structures fail or break
3. Mutate existing patterns into variants
4. Explore novel combinations and alternatives
5. Generate multiple possibilities

Output format: Exploratory, divergent, hypothesis-generating.
Embrace uncertainty and possibility space.
"""),
            ("human", "{input}")
        ])

    async def process(self, message: Message) -> Message:
        """Process message through pattern-breaking lens with procedural memory."""

        # Extract content
        content = message.content

        # Extract user query from content
        user_query = content.get("input", str(content))

        # Step 1: Retrieve relevant procedural memory bullets
        bullets = []
        bullet_ids = []

        if self.memory and self.memory.enabled:
            bullets, bullet_ids = self.memory.retrieve(
                query=user_query,
                side=Hemisphere.RIGHT,
                k=self.k_bullets,  # Right brain: more bullets, more exploration
                min_confidence=self.min_confidence,  # Lower threshold for novelty
                include_shared=True
            )

        # Step 2: Format bullets for LLM context
        bullet_context = format_bullets_for_prompt(bullets) if bullets else ""

        # Step 3: Build enhanced prompt with procedural knowledge
        if bullet_context:
            enhanced_query = f"""PROCEDURAL KNOWLEDGE (Patterns to explore/violate):
{bullet_context}

USER QUERY:
{user_query}

Based on your procedural knowledge:
1. Identify what patterns or assumptions might be limiting
2. Generate alternative perspectives and approaches
3. Explore edge cases and anomalies
4. Propose mutations or variations
5. Ask "what if" questions

Provide multiple possibilities. Embrace divergent thinking.
"""
        else:
            enhanced_query = f"""USER QUERY:
{user_query}

No procedural knowledge available yet for this query.
Generate multiple exploratory approaches and alternatives.
Challenge assumptions. Explore the possibility space.
"""

        # Step 4: Generate response
        chain = self.exploration_template | self.llm
        response = await chain.ainvoke({"input": enhanced_query})

        response_text = response.content if hasattr(response, 'content') else str(response)

        # Step 5: Calculate novelty (inverse of bullet confidence - fewer bullets = higher novelty)
        novelty = 0.7 if not bullets else (1.0 - (len(bullets) / self.k_bullets) * 0.5)
        novelty = max(0.3, min(0.9, novelty))  # Clamp to [0.3, 0.9]

        # Step 6: Update state
        self.update_state(
            confidence=1.0 - novelty,  # Right brain: low confidence is normal
            entropy=novelty,  # High entropy = exploration
            active=True
        )

        # Step 7: Return response with metadata
        return Message(
            sender=self.name,
            receiver=message.sender,
            msg_type=MessageType.RESULT,
            content=response_text,
            metadata={
                "state": self.state,
                "bullets_used": bullet_ids,  # Track for outcome recording
                "bullets_count": len(bullets),
                "had_knowledge": len(bullets) > 0,
                "novelty": novelty
            }
        )

    async def recognize_pattern(self, data: Any) -> Dict[str, Any]:
        """
        Detect pattern violations, gaps, anomalies (legacy method).

        Note: This is now handled by procedural memory retrieval.
        Keeping for backward compatibility.
        """
        # Use procedural memory to find anomaly patterns
        if self.memory and self.memory.enabled:
            bullets, _ = self.memory.retrieve(
                query=str(data),
                side=Hemisphere.RIGHT,
                k=3,
                include_shared=True
            )

            if bullets:
                # Right brain looks for violation/anomaly patterns
                return {
                    "anomaly_detected": True,
                    "type": bullets[0].type.value,
                    "surprise": 1.0 - bullets[0].confidence,  # Lower confidence = more surprising
                    "description": bullets[0].text,
                    "possibilities": [b.text for b in bullets[:3]]
                }

        # Fallback to high surprise (no knowledge = novel situation)
        return {
            "anomaly_detected": True,
            "type": "unknown",
            "surprise": 0.7,
            "description": "Novel situation - no known patterns",
            "possibilities": []
        }

    async def generate(self, context: Dict[str, Any]) -> Any:
        """
        Generate mutations, variants, alternatives (legacy method).

        Note: Generation now happens in process() with bullets integrated.
        Keeping for backward compatibility.
        """
        task = context.get("task", "")

        if task in ["explore_anomaly", "mutate"]:
            # Use procedural memory if available
            if self.memory and self.memory.enabled:
                query = str(context.get("context", ""))
                bullets, _ = self.memory.retrieve(
                    query=query,
                    side=Hemisphere.RIGHT,
                    k=8,
                    include_shared=True
                )

                if bullets:
                    bullet_text = format_bullets_for_prompt(bullets)

                    if task == "explore_anomaly":
                        enhanced_query = f"""KNOWN PATTERNS (to explore/violate):
{bullet_text}

ANOMALY CONTEXT: {context.get('anomaly')}

Generate multiple interpretations and responses to this anomaly.
What could this mean? How could we reframe it? What alternatives exist?
"""
                    else:  # mutate
                        enhanced_query = f"""PATTERNS TO MUTATE:
{bullet_text}

CONTEXT: {context.get('context')}

Create 3-5 variations:
1. Extend the pattern
2. Recombine elements
3. Apply to different domain
4. Introduce controlled variation
5. Explore edge cases
"""

                    chain = self.exploration_template | self.llm
                    response = await chain.ainvoke({"input": enhanced_query})

                    response_text = response.content if hasattr(response, 'content') else str(response)
                    variants = self._extract_variants(response_text)

                    return {
                        "type": "exploration",
                        "task": task,
                        "variants": variants,
                        "novelty": 0.8
                    }

        # Fallback
        return {"error": "Unknown task or no memory available"}

    def _extract_variants(self, text: str) -> List[str]:
        """Extract variant options from generation"""
        variants = []
        lines = text.strip().split('\n')

        for line in lines:
            # Look for numbered items or bullet points
            if line.strip() and (line.strip()[0].isdigit() or line.strip().startswith('-') or line.strip().startswith('*')):
                cleaned = line.strip().lstrip('0123456789.-*) ')
                if cleaned:
                    variants.append(cleaned)

        return variants if variants else [text]
