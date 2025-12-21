"""Base agent class for bicameral brain hemispheres"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import time


class MessageType(Enum):
    TASK = "task"
    RESULT = "result"
    QUERY = "query"
    CONFLICT = "conflict"
    SIGNAL = "signal"


@dataclass
class Message:
    sender: str
    receiver: str
    msg_type: MessageType
    content: Any
    metadata: Dict[str, Any]
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class BrainAgent(ABC):
    """Abstract base class for brain hemisphere agents"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.memory = []
        self.state = {
            "last_pattern": None,
            "confidence": 0.0,
            "entropy": 0.0,
            "active": False
        }
    
    @abstractmethod
    async def process(self, message: Message) -> Message:
        """Process incoming message and return response"""
        pass
    
    @abstractmethod
    async def recognize_pattern(self, data: Any) -> Dict[str, Any]:
        """Recognize patterns in data"""
        pass
    
    @abstractmethod
    async def generate(self, context: Dict[str, Any]) -> Any:
        """Generate output based on hemisphere specialty"""
        pass
    
    def update_state(self, **kwargs):
        """Update internal state"""
        self.state.update(kwargs)
        
    def add_to_memory(self, item: Any):
        """Add item to short-term memory"""
        self.memory.append({
            "item": item,
            "timestamp": time.time()
        })
        
        # Limit memory size
        if len(self.memory) > self.config.get("memory_limit", 20):
            self.memory.pop(0)
    
    def get_state_metrics(self) -> Dict[str, float]:
        """Return current state metrics for meta-controller"""
        return {
            "confidence": self.state["confidence"],
            "entropy": self.state["entropy"],
            "memory_load": len(self.memory) / self.config.get("memory_limit", 20)
        }
