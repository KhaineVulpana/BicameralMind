"""Procedure (playbook) store for multi-step procedural workflows."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from loguru import logger


class ProcedureStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class ProcedureStepType(str, Enum):
    BULLET = "bullet"
    TEXT = "text"
    TOOL = "tool"


@dataclass
class ProcedureStep:
    step_type: ProcedureStepType
    ref_id: Optional[str] = None
    text: Optional[str] = None
    tool_name: Optional[str] = None
    params_template: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.step_type.value,
            "ref_id": self.ref_id,
            "text": self.text,
            "tool_name": self.tool_name,
            "params_template": self.params_template,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProcedureStep":
        step_type = ProcedureStepType(data.get("type", "text"))
        return cls(
            step_type=step_type,
            ref_id=data.get("ref_id"),
            text=data.get("text"),
            tool_name=data.get("tool_name"),
            params_template=data.get("params_template"),
        )


@dataclass
class Procedure:
    id: str
    title: str
    description: str
    side: str
    tags: List[str] = field(default_factory=list)
    steps: List[ProcedureStep] = field(default_factory=list)
    status: ProcedureStatus = ProcedureStatus.DRAFT
    helpful_count: int = 0
    harmful_count: int = 0
    created_at: str = field(default_factory=lambda: _now_iso())
    updated_at: str = field(default_factory=lambda: _now_iso())
    source_trace_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "side": self.side,
            "tags": self.tags,
            "steps": [step.to_dict() for step in self.steps],
            "status": self.status.value,
            "helpful_count": self.helpful_count,
            "harmful_count": self.harmful_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "source_trace_id": self.source_trace_id,
            "metadata": self.metadata or {},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Procedure":
        steps = [ProcedureStep.from_dict(item) for item in (data.get("steps") or [])]
        status = ProcedureStatus(data.get("status", ProcedureStatus.DRAFT.value))
        return cls(
            id=data.get("id", _make_id()),
            title=data.get("title", ""),
            description=data.get("description", ""),
            side=data.get("side", "shared"),
            tags=list(data.get("tags") or []),
            steps=steps,
            status=status,
            helpful_count=int(data.get("helpful_count", 0)),
            harmful_count=int(data.get("harmful_count", 0)),
            created_at=data.get("created_at", _now_iso()),
            updated_at=data.get("updated_at", _now_iso()),
            source_trace_id=data.get("source_trace_id", ""),
            metadata=data.get("metadata") or {},
        )


def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _make_id() -> str:
    timestamp = int(datetime.utcnow().timestamp() * 1000)
    return f"proc_{timestamp}_{str(uuid4())[:8]}"


class ProcedureStore:
    """JSONL-backed store for procedures."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = (config or {}).get("procedures", {})
        self.path = Path(cfg.get("path", "./data/memory/procedures.jsonl"))
        self._cache: Dict[str, Procedure] = {}
        self._loaded = False

    def load(self) -> None:
        if not self.path.exists():
            self._loaded = True
            return
        self._cache = {}
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    proc = Procedure.from_dict(data)
                    self._cache[proc.id] = proc
                except Exception as exc:
                    logger.warning(f"Failed to parse procedure line: {exc}")
        self._loaded = True

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as handle:
            for proc in self._cache.values():
                handle.write(json.dumps(proc.to_dict()) + "\n")

    def list(
        self,
        side: Optional[str] = None,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[Procedure]:
        if not self._loaded:
            self.load()
        items = list(self._cache.values())
        if side:
            items = [p for p in items if p.side == side]
        if status:
            items = [p for p in items if p.status.value == status]
        if tags:
            items = [p for p in items if any(tag in p.tags for tag in tags)]
        return items[:limit]

    def get(self, proc_id: str) -> Optional[Procedure]:
        if not self._loaded:
            self.load()
        return self._cache.get(proc_id)

    def create(self, proc: Procedure, save: bool = True) -> Procedure:
        if not proc.id:
            proc.id = _make_id()
        proc.created_at = proc.created_at or _now_iso()
        proc.updated_at = _now_iso()
        self._cache[proc.id] = proc
        if save:
            self.save()
        return proc

    def update(self, proc_id: str, updates: Dict[str, Any], save: bool = True) -> Optional[Procedure]:
        proc = self.get(proc_id)
        if not proc:
            return None
        for key, value in updates.items():
            if key == "steps" and isinstance(value, list):
                proc.steps = [ProcedureStep.from_dict(item) for item in value]
            elif key == "status":
                try:
                    proc.status = ProcedureStatus(value)
                except ValueError:
                    continue
            elif hasattr(proc, key):
                setattr(proc, key, value)
        proc.updated_at = _now_iso()
        if save:
            self.save()
        return proc

    def delete(self, proc_id: str, save: bool = True) -> bool:
        if not self._loaded:
            self.load()
        if proc_id not in self._cache:
            return False
        self._cache.pop(proc_id, None)
        if save:
            self.save()
        return True

    def search(self, query: str, limit: int = 20) -> List[Procedure]:
        if not self._loaded:
            self.load()
        q = query.lower().strip()
        if not q:
            return []
        results: List[Procedure] = []
        for proc in self._cache.values():
            hay = " ".join([proc.title, proc.description, " ".join(proc.tags)]).lower()
            if q in hay:
                results.append(proc)
        return results[:limit]

    def record_outcome(self, proc_id: str, helpful: bool, save: bool = True) -> bool:
        proc = self.get(proc_id)
        if not proc:
            return False
        if helpful:
            proc.helpful_count += 1
        else:
            proc.harmful_count += 1
        proc.updated_at = _now_iso()
        if save:
            self.save()
        return True
