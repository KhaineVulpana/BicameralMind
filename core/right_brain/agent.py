"""Right Brain: Pattern Violation and Mutation"""
from core.base_agent import BrainAgent, Message, MessageType
from core.memory import ProceduralMemory, Bullet, Hemisphere
from typing import Dict, Any, List
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

    def __init__(self, config: Dict[str, Any], llm_client, procedural_memory: ProceduralMemory | None = None):
        super().__init__("RightBrain", config.get("right_brain", {}))
        self.llm = llm_client
        self.procedural_memory = procedural_memory
        self.hemisphere = Hemisphere.RIGHT
        self.anomalies = []
        self.mutations = []
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
    
    def _format_playbook(self, bullets: List[Bullet]) -> str:
        """Format bullets as playbook for prompt context."""
        if not bullets:
            return "(none)"

        if self.procedural_memory:
            return self.procedural_memory.format_bullets_for_prompt(bullets)

        # Fallback simple format
        lines = []
        for b in bullets:
            prefix = "[SHARED]" if b.side == Hemisphere.SHARED else "[RIGHT]"
            lines.append(f"- {prefix} ({b.type.value}, conf={b.confidence:.2f}, +{b.helpful_count}/-{b.harmful_count}): {b.text}")
        return "\n".join(lines)

    async def process(self, message: Message) -> Message:
        """Process message through pattern-breaking lens"""
        
        content = message.content

        # Retrieve procedural guidance (ACE-style bullets)
        playbook_bullets: List[Bullet] = []
        used_bullet_ids: List[str] = []
        if self.procedural_memory and self.procedural_memory.enabled:
            q = content.get("input") if isinstance(content, dict) else str(content)
            playbook_bullets, used_bullet_ids = self.procedural_memory.retrieve(
                query=str(q),
                side=self.hemisphere,
                k=16,  # Right brain uses more bullets, explores more
                min_confidence=0.4,  # Lower threshold, more exploratory
            )
        
        # Detect violations/anomalies
        anomaly_check = await self.recognize_pattern(content, playbook_bullets)
        
        # Generate variants/mutations
        if anomaly_check["anomaly_detected"]:
            response = await self.generate({
                "task": "explore_anomaly",
                "anomaly": anomaly_check,
                "context": content
            }, playbook_bullets)
        else:
            # Generate mutations anyway (exploration mode)
            response = await self.generate({
                "task": "mutate",
                "context": content
            }, playbook_bullets)
        
        # Update state
        self.update_state(
            confidence=1.0 - anomaly_check.get("surprise", 0.5),
            entropy=anomaly_check.get("surprise", 0.5),
            last_pattern=anomaly_check.get("type"),
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
        """Detect pattern violations, gaps, anomalies"""
        
        query = f"""Analyze this input for pattern violations:
1. Does this break expected structure?
2. Are there anomalies, gaps, or contradictions?
3. What's surprising or unexpected?
4. What doesn't fit known models?

Procedural playbook (strategies/heuristics to use while exploring):
{self._format_playbook(playbook or [])}

Input: {data}

Recent anomalies: {self.anomalies[-3:] if self.anomalies else 'None yet'}

Respond in format:
ANOMALY_DETECTED: yes/no
TYPE: [violation/gap/contradiction/surprise]
SURPRISE_LEVEL: [0.0-1.0]
DESCRIPTION: [what's broken/unexpected]
POSSIBILITIES: [list alternative interpretations]
"""
        
        chain = self.exploration_template | self.llm
        response = await chain.ainvoke({"input": query})
        
        result = self._parse_anomaly(response.content if hasattr(response, 'content') else str(response))
        
        # Store anomalies
        if result["anomaly_detected"]:
            self.anomalies.append({
                "type": result.get("type"),
                "data": data,
                "surprise": result.get("surprise", 0.5)
            })
        
        return result
    
    async def generate(self, context: Dict[str, Any], playbook: List[Bullet] | None = None) -> Any:
        """Generate mutations, variants, alternatives"""
        
        if context["task"] == "explore_anomaly":
            query = f"""This is an anomaly/pattern violation:
{context['anomaly']}

Procedural playbook (use these as prompts/constraints):
{self._format_playbook(playbook or [])}

Generate multiple possible interpretations and responses:
1. What could this mean?
2. How could we reframe this?
3. What alternatives exist?
4. What new patterns could emerge?

Be divergent. Generate options.
"""
        
        elif context["task"] == "mutate":
            query = f"""Mutate this pattern into variants:
Context: {context.get('context')}

Procedural playbook (use these heuristics):
{self._format_playbook(playbook or [])}

Create 3-5 variations:
1. Extend the pattern
2. Recombine elements
3. Apply to different domain
4. Introduce controlled variation
5. Explore edge cases
"""
        
        else:
            return {"error": "Unknown task"}
        
        chain = self.exploration_template | self.llm
        response = await chain.ainvoke({"input": query})
        
        variants = self._extract_variants(response.content if hasattr(response, 'content') else str(response))
        
        # Store mutations
        self.mutations.append({
            "context": context,
            "variants": variants,
            "count": len(variants)
        })
        
        return {
            "type": "exploration",
            "task": context["task"],
            "variants": variants,
            "novelty": context.get("anomaly", {}).get("surprise", 0.7)
        }
    
    def _parse_anomaly(self, text: str) -> Dict[str, Any]:
        """Parse anomaly detection response"""
        lines = text.strip().split('\n')
        result = {
            "anomaly_detected": False,
            "type": None,
            "surprise": 0.5,
            "description": "",
            "possibilities": []
        }
        
        for line in lines:
            if "ANOMALY_DETECTED:" in line:
                result["anomaly_detected"] = "yes" in line.lower()
            elif "TYPE:" in line:
                result["type"] = line.split(":", 1)[1].strip()
            elif "SURPRISE_LEVEL:" in line:
                try:
                    result["surprise"] = float(line.split(":", 1)[1].strip())
                except:
                    result["surprise"] = 0.5
            elif "DESCRIPTION:" in line:
                result["description"] = line.split(":", 1)[1].strip()
            elif "POSSIBILITIES:" in line:
                poss = line.split(":", 1)[1].strip()
                result["possibilities"] = [p.strip() for p in poss.split(",") if p.strip()]
        
        return result
    
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
