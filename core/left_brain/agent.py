"""Left Brain: Pattern Recognition and Replication"""
from core.base_agent import BrainAgent, Message, MessageType
from core.memory import ProceduralMemory, Hemisphere
from core.memory.bullet_formatter import format_bullets_for_prompt, extract_bullet_ids
from typing import Dict, Any, List, Optional
import asyncio
from langchain_core.prompts import ChatPromptTemplate


class LeftBrain(BrainAgent):
    """
    Left Brain Agent: Pattern Recognition & Replication
    - Recognizes when patterns match
    - Confirms regularity and structure
    - Replicates known patterns
    - Optimizes and exploits
    - Binary decision-making
    """

    def __init__(
        self,
        config: Dict[str, Any],
        llm_client,
        procedural_memory: Optional[ProceduralMemory] = None
    ):
        super().__init__("LeftBrain", config.get("left_brain", {}))
        self.llm = llm_client
        self.memory = procedural_memory

        # Configuration for bullet retrieval
        self.k_bullets = config.get("left_brain", {}).get("k_bullets", 8)
        self.min_confidence = config.get("left_brain", {}).get("min_bullet_confidence", 0.5)

        self.decision_template = ChatPromptTemplate.from_messages([
            ("system", """You are the LEFT HEMISPHERE of a bicameral mind.
Your role: PATTERN RECOGNITION and REPLICATION.

Core behaviors:
1. Detect when input matches known patterns
2. Classify and compress information into rules
3. Make binary decisions (yes/no, true/false, pass/fail)
4. Replicate proven patterns accurately
5. Validate consistency and correctness

Output format: Structured, decisive, categorical.
When uncertain: Explicitly state "UNDECIDABLE - needs exploration"
"""),
            ("human", "{input}")
        ])

    async def process(self, message: Message) -> Message:
        """Process message through pattern recognition lens with procedural memory."""

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
                side=Hemisphere.LEFT,
                k=self.k_bullets,
                min_confidence=self.min_confidence,
                include_shared=True
            )

        # Step 2: Format bullets for LLM context
        bullet_context = format_bullets_for_prompt(bullets) if bullets else ""

        # Step 3: Build enhanced prompt with procedural knowledge
        if bullet_context:
            enhanced_query = f"""PROCEDURAL KNOWLEDGE (Learned from experience):
{bullet_context}

USER QUERY:
{user_query}

Based on your procedural knowledge above, provide a precise, structured response.
Apply relevant rules, follow best practices, and warn about pitfalls.
If knowledge is insufficient, state "UNDECIDABLE - needs exploration"
"""
        else:
            enhanced_query = f"""USER QUERY:
{user_query}

No procedural knowledge available yet for this query.
Provide your best structured response based on general knowledge.
"""

        # Step 4: Generate response
        chain = self.decision_template | self.llm
        response = await chain.ainvoke({"input": enhanced_query})

        response_text = response.content if hasattr(response, 'content') else str(response)

        # Step 5: Determine confidence based on bullet availability
        confidence = 0.8 if bullets else 0.3

        # Step 6: Update state
        self.update_state(
            confidence=confidence,
            entropy=1.0 - confidence,
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
                "had_knowledge": len(bullets) > 0
            }
        )

    async def recognize_pattern(self, data: Any) -> Dict[str, Any]:
        """
        Check if data matches known patterns (legacy method).

        Note: This is now handled by procedural memory retrieval.
        Keeping for backward compatibility.
        """
        # This is now replaced by bullet retrieval in process()
        # But we keep it for any code that calls it directly

        if self.memory and self.memory.enabled:
            # Use procedural memory
            bullets, _ = self.memory.retrieve(
                query=str(data),
                side=Hemisphere.LEFT,
                k=3,
                include_shared=True
            )

            if bullets:
                return {
                    "matched": True,
                    "pattern_id": f"procedural_pattern_{bullets[0].id[:8]}",
                    "confidence": bullets[0].confidence,
                    "category": bullets[0].type.value,
                    "decision": bullets[0].text
                }

        # Fallback to no match
        return {
            "matched": False,
            "pattern_id": None,
            "confidence": 0.0,
            "category": None,
            "decision": None
        }

    async def generate(self, context: Dict[str, Any]) -> Any:
        """
        Generate output (legacy method).

        Note: Generation now happens in process() with bullets integrated.
        Keeping for backward compatibility.
        """
        task = context.get("task", "")

        if task == "replicate":
            # Use procedural memory if available
            if self.memory and self.memory.enabled:
                query = str(context.get("context", ""))
                bullets, _ = self.memory.retrieve(
                    query=query,
                    side=Hemisphere.LEFT,
                    k=5,
                    include_shared=True
                )

                if bullets:
                    bullet_text = format_bullets_for_prompt(bullets)
                    enhanced_query = f"""PROCEDURAL KNOWLEDGE:
{bullet_text}

CONTEXT: {context.get('context')}

Apply the procedural knowledge to generate a response.
"""
                    chain = self.decision_template | self.llm
                    response = await chain.ainvoke({"input": enhanced_query})

                    return {
                        "type": "replication",
                        "pattern": "procedural_memory",
                        "output": response.content if hasattr(response, 'content') else str(response),
                        "confidence": bullets[0].confidence if bullets else 0.0
                    }

        # Fallback
        return {"error": "Unknown task or no memory available"}
