"""Suggestion store for cross-hemisphere teaching."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4


def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    except Exception:
        return None


def _make_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


@dataclass
class Suggestion:
    suggestion_id: str
    from_side: str
    to_side: str
    origin_bullet_id: str
    suggested_text: str
    tags: List[str]
    reason: str
    status: str
    created_at: str
    delivered_at: Optional[str] = None
    resolved_at: Optional[str] = None
    trace_ids: List[str] = field(default_factory=list)
    delivered_bullet_id: Optional[str] = None
    resolution_reason: str = ""

    def to_dict(self) -> Dict:
        return {
            "suggestion_id": self.suggestion_id,
            "from_side": self.from_side,
            "to_side": self.to_side,
            "origin_bullet_id": self.origin_bullet_id,
            "suggested_text": self.suggested_text,
            "tags": self.tags,
            "reason": self.reason,
            "status": self.status,
            "created_at": self.created_at,
            "delivered_at": self.delivered_at,
            "resolved_at": self.resolved_at,
            "trace_ids": self.trace_ids,
            "delivered_bullet_id": self.delivered_bullet_id,
            "resolution_reason": self.resolution_reason,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Suggestion":
        return cls(
            suggestion_id=data["suggestion_id"],
            from_side=data["from_side"],
            to_side=data["to_side"],
            origin_bullet_id=data.get("origin_bullet_id", ""),
            suggested_text=data.get("suggested_text", ""),
            tags=data.get("tags", []) or [],
            reason=data.get("reason", ""),
            status=data.get("status", "pending"),
            created_at=data.get("created_at", _now_iso()),
            delivered_at=data.get("delivered_at"),
            resolved_at=data.get("resolved_at"),
            trace_ids=data.get("trace_ids", []) or [],
            delivered_bullet_id=data.get("delivered_bullet_id"),
            resolution_reason=data.get("resolution_reason", ""),
        )


class SuggestionStore:
    """File-backed store for cross-hemisphere suggestions."""

    def __init__(self, path: str):
        raw_path = path
        resolved = Path(path)
        if resolved.exists() and resolved.is_dir():
            resolved = resolved / "suggestions.jsonl"
        elif raw_path.endswith(("/", "\\")):
            resolved = resolved / "suggestions.jsonl"
        self.path = resolved
        self._items: Dict[str, Suggestion] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            for line in self.path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                suggestion = Suggestion.from_dict(data)
                self._items[suggestion.suggestion_id] = suggestion
        except Exception:
            # If the file is corrupted, start from what was parsed.
            pass

    def _write_all(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        items = sorted(
            self._items.values(),
            key=lambda s: (s.created_at, s.suggestion_id),
        )
        lines = [json.dumps(item.to_dict(), ensure_ascii=True) for item in items]
        tmp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        tmp_path.replace(self.path)

    def create(self, suggestion: Suggestion) -> str:
        if not suggestion.suggestion_id:
            suggestion.suggestion_id = _make_id("sg")
        if not suggestion.created_at:
            suggestion.created_at = _now_iso()
        if suggestion.suggestion_id in self._items:
            raise ValueError(f"Suggestion already exists: {suggestion.suggestion_id}")
        self._items[suggestion.suggestion_id] = suggestion
        self._write_all()
        return suggestion.suggestion_id

    def list_pending(self, to_side: Optional[str] = None) -> List[Suggestion]:
        pending = [
            s for s in self._items.values()
            if s.status == "pending" and (to_side is None or s.to_side == to_side)
        ]
        return sorted(pending, key=lambda s: (s.created_at, s.suggestion_id))

    def count(self, status: Optional[str] = None) -> int:
        if status is None:
            return len(self._items)
        return sum(1 for s in self._items.values() if s.status == status)

    def get(self, suggestion_id: str) -> Optional[Suggestion]:
        return self._items.get(suggestion_id)

    def mark_delivered(self, suggestion_id: str, delivered_bullet_id: Optional[str] = None) -> None:
        suggestion = self._items.get(suggestion_id)
        if not suggestion:
            return
        suggestion.status = "delivered"
        suggestion.delivered_at = suggestion.delivered_at or _now_iso()
        if delivered_bullet_id:
            suggestion.delivered_bullet_id = delivered_bullet_id
        self._write_all()

    def resolve(self, suggestion_id: str, accepted: bool, reason: str = "") -> None:
        suggestion = self._items.get(suggestion_id)
        if not suggestion:
            return
        suggestion.status = "accepted" if accepted else "rejected"
        suggestion.resolved_at = _now_iso()
        if reason:
            suggestion.resolution_reason = reason
        self._write_all()

    def expire_old(self, max_age_days: int) -> int:
        if max_age_days <= 0:
            return 0
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
        expired = 0
        for suggestion in self._items.values():
            if suggestion.status not in ("pending", "delivered"):
                continue
            ts = suggestion.delivered_at if suggestion.status == "delivered" else suggestion.created_at
            parsed = _parse_iso(ts)
            if parsed and parsed < cutoff:
                suggestion.status = "expired"
                suggestion.resolved_at = _now_iso()
                expired += 1
        if expired:
            self._write_all()
        return expired

    def exists_active(self, origin_bullet_id: str, to_side: Optional[str] = None) -> bool:
        for suggestion in self._items.values():
            if suggestion.origin_bullet_id != origin_bullet_id:
                continue
            if to_side and suggestion.to_side != to_side:
                continue
            if suggestion.status in ("pending", "delivered"):
                return True
        return False
