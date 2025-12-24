"""Left Brain: Pattern Recognition and Replication"""
from core.base_agent import BrainAgent, Message, MessageType
from core.memory import ProceduralMemory, Bullet, Hemisphere
from typing import Dict, Any, List
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

    def __init__(self, config: Dict[str, Any], llm_client, procedural_memory: ProceduralMemory | None = None):
        super().__init__("LeftBrain", config.get("left_brain", {}))
        self.llm = llm_client
        self.procedural_memory = procedural_memory
        self.hemisphere = Hemisphere.LEFT
        self.known_patterns = []
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

    def _format_playbook(self, bullets: List[Bullet]) -> str:
        """Format bullets as playbook for prompt context."""
        if not bullets:
            return "(none)"

        if self.procedural_memory:
            return self.procedural_memory.format_bullets_for_prompt(bullets)

        # Fallback simple format
        lines = []
        for b in bullets:
            prefix = "[SHARED]" if b.side == Hemisphere.SHARED else "[LEFT]"
            lines.append(f"- {prefix} ({b.type.value}, conf={b.confidence:.2f}, +{b.helpful_count}/-{b.harmful_count}): {b.text}")
        return "\n".join(lines)
    
    async def process(self, message: Message) -> Message:
        """Process message through pattern recognition lens"""
        
        # Extract content
        content = message.content

        # Retrieve procedural guidance (ACE-style bullets)
        playbook_bullets: List[Bullet] = []
        used_bullet_ids: List[str] = []
        if self.procedural_memory and self.procedural_memory.enabled:
            q = content.get("input") if isinstance(content, dict) else str(content)
            playbook_bullets, used_bullet_ids = self.procedural_memory.retrieve(
                query=str(q),
                side=self.hemisphere,
                k=8,  # Left brain uses fewer, higher-confidence bullets
                min_confidence=0.6,
            )
        
        # Recognize pattern
        pattern_match = await self.recognize_pattern(content, playbook_bullets)
        
        # Generate response based on pattern match
        if pattern_match["matched"]:
            response = await self.generate({
                "task": "replicate",
                "pattern": pattern_match,
                "context": content
            }, playbook_bullets)
        else:
            response = {
                "status": "no_match",
                "signal": "EXPLORATION_NEEDED",
                "confidence": 0.0
            }
        
        # Update state
        self.update_state(
            confidence=pattern_match.get("confidence", 0.0),
            entropy=1.0 - pattern_match.get("confidence", 0.0),
            last_pattern=pattern_match.get("pattern_id"),
            active=True
        )
        
        return Message(
            sender=self.name,
            receiver=message.sender,
            msg_type=MessageType.RESULT,
            content=response,
            metadata={"state": self.state, "used_bullet_ids": used_bullet_ids}
        )
    
    async def recognize_pattern(self, data: Any, playbook: List[Bullet] | None = None) -> Dict[str, Any]:
        """Check if data matches known patterns"""
        
        # Prepare recognition query
        query = f"""Analyze this input and determine:
1. Does it match a known structure/pattern?
2. Can it be classified categorically?
3. Is there a clear decision boundary?

Procedural playbook (strategies/rules to follow):
{self._format_playbook(playbook or [])}

Input: {data}

Known patterns: {self.known_patterns[:5] if self.known_patterns else 'None yet'}

Respond in format:
MATCHED: yes/no
PATTERN_ID: [identifier if matched]
CONFIDENCE: [0.0-1.0]
CATEGORY: [if applicable]
DECISION: [if decidable]
"""
        
        # Query LLM
        chain = self.decision_template | self.llm
        response = await chain.ainvoke({"input": query})
        
        # Parse response
        result = self._parse_recognition(response.content if hasattr(response, 'content') else str(response))
        
        # Store if new pattern
        if result["matched"] and result.get("pattern_id"):
            self._store_pattern(result["pattern_id"], data)
        
        return result
    
    async def generate(self, context: Dict[str, Any], playbook: List[Bullet] | None = None) -> Any:
        """Generate output by replicating known pattern"""
        
        if context["task"] == "replicate":
            pattern = context["pattern"]
            
            query = f"""Replicate this pattern accurately:
Pattern: {pattern.get('pattern_id')}
Context: {context.get('context')}

Procedural playbook (follow these rules/checklists where relevant):
{self._format_playbook(playbook or [])}

Apply the known pattern to generate a response.
Maintain consistency and structure.
"""
            
            chain = self.decision_template | self.llm
            response = await chain.ainvoke({"input": query})
            
            return {
                "type": "replication",
                "pattern": pattern.get("pattern_id"),
                "output": response.content if hasattr(response, 'content') else str(response),
                "confidence": pattern.get("confidence", 0.0)
            }
        
        return {"error": "Unknown task"}
    
    def _parse_recognition(self, text: str) -> Dict[str, Any]:
        """Parse LLM recognition response"""
        lines = text.strip().split('\n')
        result = {
            "matched": False,
            "pattern_id": None,
            "confidence": 0.0,
            "category": None,
            "decision": None
        }
        
        for line in lines:
            if "MATCHED:" in line:
                result["matched"] = "yes" in line.lower()
            elif "PATTERN_ID:" in line:
                result["pattern_id"] = line.split(":", 1)[1].strip()
            elif "CONFIDENCE:" in line:
                try:
                    result["confidence"] = float(line.split(":", 1)[1].strip())
                except:
                    result["confidence"] = 0.5
            elif "CATEGORY:" in line:
                result["category"] = line.split(":", 1)[1].strip()
            elif "DECISION:" in line:
                result["decision"] = line.split(":", 1)[1].strip()
        
        return result
    
    def _store_pattern(self, pattern_id: str, example: Any):
        """Store recognized pattern"""
        if not any(p["id"] == pattern_id for p in self.known_patterns):
            self.known_patterns.append({
                "id": pattern_id,
                "examples": [example],
                "count": 1
            })
        else:
            for p in self.known_patterns:
                if p["id"] == pattern_id:
                    p["examples"].append(example)
                    p["count"] += 1
                    break
