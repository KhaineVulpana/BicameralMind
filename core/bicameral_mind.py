"""Bicameral Mind: Main Orchestrator"""
import asyncio
from typing import Dict, Any, Optional, List
import yaml
from loguru import logger
from langchain_community.llms import Ollama

from core.left_brain.agent import LeftBrain
from core.right_brain.agent import RightBrain
from core.meta_controller.controller import MetaController, CognitiveMode
from core.base_agent import Message, MessageType
from integrations.rag.agentic_rag import AgenticRAG
from core.memory import ProceduralMemory


class BicameralMind:
    """
    Bicameral Mind: A2A System with Consciousness Ticks
    
    Architecture:
    - Left Brain: Pattern recognition & replication
    - Right Brain: Pattern breaking & mutation  
    - Meta-Controller: Consciousness tick system
    - Agentic RAG: Iterative knowledge retrieval
    """
    
    def __init__(self, config_path: Any = "config/config.yaml"):
        # Load config
        if isinstance(config_path, dict):
            self.config = config_path
        else:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        
        # Initialize LLM
        model_config = self.config.get("model", {})
        self.llm = Ollama(
            model=model_config.get("name", "qwen2.5:14b"),
            temperature=model_config.get("temperature", 0.7)
        )
        
        # Initialize brain hemispheres
        self.left_brain = LeftBrain(self.config, self.llm)
        self.right_brain = RightBrain(self.config, self.llm)
        
        # Initialize meta-controller
        self.meta_controller = MetaController(
            self.config,
            self.left_brain,
            self.right_brain
        )
        
        # Initialize procedural memory
        self.memory = ProceduralMemory(self.config)

        # Initialize RAG if enabled
        self.rag = None
        if self.config.get("rag", {}).get("enabled", False):
            self.rag = AgenticRAG(self.config, self.llm)
        
        # State
        self.running = False
        self.conversation_history = []
        
        logger.info("🧠 Bicameral Mind initialized")
    
    async def start(self):
        """Start the bicameral mind system"""
        self.running = True
        
        # Start meta-controller tick system
        asyncio.create_task(self.meta_controller.start_ticker())
        
        logger.success("✨ Bicameral Mind activated")
    
    def stop(self):
        """Stop the system"""
        self.running = False
        self.meta_controller.stop_ticker()
        logger.info("Bicameral Mind deactivated")
    
    async def process(self, user_input: str, use_rag: bool = True) -> Dict[str, Any]:
        """
        Process user input through the bicameral mind
        
        Flow:
        1. Check meta-controller for active hemisphere
        2. Retrieve knowledge if RAG enabled
        3. Process through appropriate brain(s)
        4. Synthesize response
        """
        
        logger.info(f"📥 Processing: '{user_input[:50]}...'")
        
        # Get context from RAG if enabled
        rag_context = None
        if use_rag and self.rag:
            rag_result = await self.rag.retrieve(
                user_input,
                mode=self.config.get("rag", {}).get("retrieval_mode", "agentic")
            )
            rag_context = {
                "answer": rag_result["answer"],
                "sources": [str(s) for s in rag_result["sources"][:3]],
                "iterations": rag_result["iterations"]
            }
            logger.debug(f"  RAG: {rag_result['iterations']} iterations")
        
        # Determine active hemisphere from meta-controller
        active = self.meta_controller.get_active_hemisphere()
        mode = self.meta_controller.mode
        
        logger.debug(f"  Mode: {mode.value} | Active: {active}")
        
        # Create message
        msg_content = {
            "input": user_input,
            "rag_context": rag_context,
            "mode": mode.value
        }
        
        # Process based on mode
        if mode == CognitiveMode.EXPLOIT:
            # Left brain dominant - pattern matching
            result = await self._process_exploit(msg_content)
        
        elif mode == CognitiveMode.EXPLORE:
            # Right brain dominant - exploration
            result = await self._process_explore(msg_content)
        
        elif mode == CognitiveMode.INTEGRATE:
            # Both brains - integration
            result = await self._process_integrate(msg_content)
        
        else:
            # Idle - default to integration
            result = await self._process_integrate(msg_content)
        
        # Add to history
        self.conversation_history.append({
            "input": user_input,
            "result": result,
            "mode": mode.value,
            "rag_used": use_rag
        })
        
        return result

    async def process_input(self, user_input: str, use_rag: bool = True) -> str:
        """Compatibility wrapper for older UI code paths."""
        result = await self.process(user_input, use_rag=use_rag)
        if isinstance(result, dict):
            return result.get("output", str(result))
        return str(result)
    
    async def _process_exploit(self, content: Dict) -> Dict[str, Any]:
        """Process through left brain (pattern matching)"""
        
        msg = Message(
            sender="user",
            receiver="LeftBrain",
            msg_type=MessageType.TASK,
            content=content,
            metadata={}
        )
        
        response = await self.left_brain.process(msg)
        
        return {
            "output": response.content,
            "hemisphere": "left",
            "mode": "exploit",
            "confidence": response.metadata.get("state", {}).get("confidence", 0.0)
        }
    
    async def _process_explore(self, content: Dict) -> Dict[str, Any]:
        """Process through right brain (exploration)"""
        
        msg = Message(
            sender="user",
            receiver="RightBrain",
            msg_type=MessageType.TASK,
            content=content,
            metadata={}
        )
        
        response = await self.right_brain.process(msg)
        
        return {
            "output": response.content,
            "hemisphere": "right",
            "mode": "explore",
            "novelty": response.metadata.get("state", {}).get("entropy", 0.0)
        }
    
    async def _process_integrate(self, content: Dict) -> Dict[str, Any]:
        """Process through both brains and integrate"""
        
        # Query both hemispheres in parallel
        left_task = self.left_brain.process(Message(
            sender="user",
            receiver="LeftBrain",
            msg_type=MessageType.TASK,
            content=content,
            metadata={}
        ))
        
        right_task = self.right_brain.process(Message(
            sender="user",
            receiver="RightBrain",
            msg_type=MessageType.TASK,
            content=content,
            metadata={}
        ))
        
        left_response, right_response = await asyncio.gather(left_task, right_task)
        
        # Integrate responses
        integrated = await self._integrate_responses(left_response, right_response, content)
        
        return {
            "output": integrated,
            "hemisphere": "both",
            "mode": "integrate",
            "left": left_response.content,
            "right": right_response.content
        }
    
    async def _integrate_responses(self, left: Message, right: Message, context: Dict) -> str:
        """Integrate left and right brain responses"""
        
        prompt = f"""Synthesize these two perspectives:

LEFT (Pattern Recognition): {left.content}

RIGHT (Exploration): {right.content}

Original query: {context.get('input')}

Provide integrated response that combines both views:"""
        
        response = await self.llm.ainvoke(prompt)
        return response if isinstance(response, str) else str(response)
    
    def get_consciousness_state(self) -> Dict[str, Any]:
        """Get current consciousness metrics"""
        return self.meta_controller.get_consciousness_metrics()
    
    def add_knowledge(self, documents: List[str]):
        """Add documents to knowledge base"""
        if self.rag:
            self.rag.add_documents(documents)
        else:
            logger.warning("RAG not enabled - cannot add knowledge")
