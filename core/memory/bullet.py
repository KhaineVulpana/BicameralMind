"""Bullet schema and types for procedural memory.

A Bullet represents a single atomic piece of procedural knowledge:
- A strategy
- A heuristic
- A failure mode
- A tool rule
- A checklist item
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional
from uuid import uuid4


class BulletType(str, Enum):
    """Type of procedural knowledge stored in a bullet."""

    TOOL_RULE = "tool_rule"          # Rules about how to use tools/APIs
    HEURISTIC = "heuristic"          # General problem-solving strategies
    CHECKLIST = "checklist"          # Step-by-step procedures
    PITFALL = "pitfall"              # Common mistakes to avoid
    TEMPLATE = "template"            # Code/text templates
    EXAMPLE = "example"              # Concrete examples
    PATTERN = "pattern"              # Recognized patterns
    CONCEPT = "concept"              # Domain concepts


class BulletStatus(str, Enum):
    """Lifecycle status of a bullet."""

    ACTIVE = "active"                # Actively used
    QUARANTINED = "quarantined"      # New, needs validation
    DEPRECATED = "deprecated"        # No longer used


class Hemisphere(str, Enum):
    """Which hemisphere owns this bullet."""

    LEFT = "left"                    # Left brain (pattern continuity)
    RIGHT = "right"                  # Right brain (pattern violation)
    SHARED = "shared"                # Consensus memory


@dataclass
class Bullet:
    """A single atomic procedural memory bullet.

    Design principles:
    - Immutable identity (id)
    - Incrementally updated metadata (helpful/harmful counts)
    - Only text is embedded for retrieval
    - All other fields are metadata for filtering/scoring
    """

    # Core identity
    id: str
    text: str
    side: Hemisphere

    # Classification
    type: BulletType = BulletType.HEURISTIC
    tags: List[str] = field(default_factory=list)

    # Lifecycle
    status: BulletStatus = BulletStatus.QUARANTINED
    confidence: float = 0.5

    # Learning signals (outcome-based, NOT tick-based)
    helpful_count: int = 0
    harmful_count: int = 0

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used_at: Optional[datetime] = None

    # Traceability
    source_trace_id: str = ""

    @staticmethod
    def generate_id(side: Hemisphere) -> str:
        """Generate a unique bullet ID."""
        timestamp = int(datetime.utcnow().timestamp() * 1000)
        short_uuid = str(uuid4())[:8]
        return f"pb_{side.value}_{timestamp}_{short_uuid}"

    @classmethod
    def create(
        cls,
        text: str,
        side: Hemisphere,
        bullet_type: BulletType = BulletType.HEURISTIC,
        tags: Optional[List[str]] = None,
        confidence: float = 0.5,
        source_trace_id: str = "",
    ) -> "Bullet":
        """Factory method to create a new bullet."""
        return cls(
            id=cls.generate_id(side),
            text=text.strip(),
            side=side,
            type=bullet_type,
            tags=tags or [],
            confidence=confidence,
            source_trace_id=source_trace_id,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "text": self.text,
            "side": self.side.value if isinstance(self.side, Hemisphere) else self.side,
            "type": self.type.value if isinstance(self.type, BulletType) else self.type,
            "tags": self.tags,
            "status": self.status.value if isinstance(self.status, BulletStatus) else self.status,
            "confidence": float(self.confidence),
            "helpful_count": int(self.helpful_count),
            "harmful_count": int(self.harmful_count),
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "last_used_at": self.last_used_at.isoformat() if isinstance(self.last_used_at, datetime) and self.last_used_at else "",
            "source_trace_id": self.source_trace_id,
        }

    def to_metadata(self) -> Dict[str, Any]:
        """Convert to metadata dict for vector store (Chroma-compatible)."""
        return {
            "id": self.id,
            "side": self.side.value if isinstance(self.side, Hemisphere) else self.side,
            "type": self.type.value if isinstance(self.type, BulletType) else self.type,
            "tags": ",".join(self.tags) if self.tags else "",
            "status": self.status.value if isinstance(self.status, BulletStatus) else self.status,
            "confidence": float(self.confidence),
            "helpful_count": int(self.helpful_count),
            "harmful_count": int(self.harmful_count),
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "last_used_at": self.last_used_at.isoformat() if isinstance(self.last_used_at, datetime) and self.last_used_at else "",
            "source_trace_id": self.source_trace_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Bullet":
        """Reconstruct from dictionary."""
        # Parse enums
        side = Hemisphere(data.get("side", "left"))
        bullet_type = BulletType(data.get("type", "heuristic"))
        status = BulletStatus(data.get("status", "active"))

        # Parse timestamps
        created_at = data.get("created_at", "")
        if isinstance(created_at, str) and created_at:
            try:
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except:
                created_at = datetime.utcnow()
        elif not isinstance(created_at, datetime):
            created_at = datetime.utcnow()

        last_used_at = data.get("last_used_at")
        if isinstance(last_used_at, str) and last_used_at:
            try:
                last_used_at = datetime.fromisoformat(last_used_at.replace("Z", "+00:00"))
            except:
                last_used_at = None
        elif not isinstance(last_used_at, datetime):
            last_used_at = None

        # Parse tags
        tags = data.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]

        return cls(
            id=data["id"],
            text=data["text"],
            side=side,
            type=bullet_type,
            tags=tags,
            status=status,
            confidence=float(data.get("confidence", 0.5)),
            helpful_count=int(data.get("helpful_count", 0)),
            harmful_count=int(data.get("harmful_count", 0)),
            created_at=created_at,
            last_used_at=last_used_at,
            source_trace_id=data.get("source_trace_id", ""),
        )

    def score(self) -> float:
        """Calculate overall quality score.

        Combines:
        - Base confidence
        - Helpful signals (positive)
        - Harmful signals (negative, weighted higher)
        """
        return self.confidence + (0.05 * self.helpful_count) - (0.1 * self.harmful_count)

    def mark_helpful(self) -> None:
        """Increment helpful counter (outcome-based signal)."""
        self.helpful_count += 1

    def mark_harmful(self) -> None:
        """Increment harmful counter (outcome-based signal)."""
        self.harmful_count += 1

    def touch(self) -> None:
        """Update last used timestamp."""
        self.last_used_at = datetime.utcnow()

    def should_promote_to_shared(self, threshold: int = 3) -> bool:
        """Check if bullet meets criteria for promotion to shared memory.

        Criteria:
        - Must be active
        - Must have >= threshold helpful signals
        - Must have zero harmful signals (high confidence required)
        - Not already in shared
        """
        return (
            self.status == BulletStatus.ACTIVE
            and self.helpful_count >= threshold
            and self.harmful_count == 0
            and self.side != Hemisphere.SHARED
        )

    def should_quarantine(self, threshold: int = 2) -> bool:
        """Check if bullet should be quarantined due to harmful signals."""
        return self.harmful_count >= threshold

    def should_activate(self, threshold: int = 2) -> bool:
        """Check if quarantined bullet should be activated.

        Criteria:
        - Currently quarantined
        - Has >= threshold helpful signals
        - Has zero harmful signals
        """
        return (
            self.status == BulletStatus.QUARANTINED
            and self.helpful_count >= threshold
            and self.harmful_count == 0
        )

    def __repr__(self) -> str:
        return (
            f"Bullet(id={self.id[:16]}..., "
            f"side={self.side.value}, "
            f"type={self.type.value}, "
            f"score={self.score():.2f}, "
            f"status={self.status.value})"
        )

    def __str__(self) -> str:
        """Human-readable bullet representation."""
        tags_str = f"[{', '.join(self.tags)}]" if self.tags else ""
        score = self.score()
        return f"[{self.type.value}]{tags_str} {self.text} (score: {score:.2f}, +{self.helpful_count}/-{self.harmful_count})"
