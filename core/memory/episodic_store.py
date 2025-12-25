"""Episodic memory store for narrative/task episodes."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger


@dataclass
class Episode:
    id: str
    title: str
    summary: str
    content: str
    side: str = "shared"  # left|right|shared
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds") + "Z")
    outcome: str = "unknown"  # success|failure|unknown
    trace_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "content": self.content,
            "side": self.side,
            "tags": self.tags,
            "created_at": self.created_at,
            "outcome": self.outcome,
            "trace_ids": self.trace_ids,
            "metadata": self.metadata or {},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Episode":
        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            summary=data.get("summary", ""),
            content=data.get("content", ""),
            side=data.get("side", "shared"),
            tags=list(data.get("tags") or []),
            created_at=data.get("created_at", datetime.utcnow().isoformat(timespec="seconds") + "Z"),
            outcome=data.get("outcome", "unknown"),
            trace_ids=list(data.get("trace_ids") or []),
            metadata=data.get("metadata") or {},
        )


class EpisodicStore:
    """JSONL + vector index store for episodic memory."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = (config or {}).get("episodic_memory", {}) or {}
        vector_cfg = (config or {}).get("vector_store", {}) or {}
        self.path = Path(cfg.get("path", "./data/memory/episodes.jsonl"))
        self.persist_directory = cfg.get("persist_directory", "./data/vector_store/episodes")
        self.embedding_model = cfg.get("embedding_model", vector_cfg.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2"))
        self.top_k = int(cfg.get("top_k", 5))

        self._cache: Dict[str, Episode] = {}
        self._loaded = False
        self._collection = None
        self._embedder = None

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()

    def _ensure_index(self) -> None:
        if self._collection is not None:
            return
        try:
            import chromadb  # type: ignore
            from chromadb.config import Settings  # type: ignore
            from sentence_transformers import SentenceTransformer  # type: ignore
        except Exception as exc:
            raise RuntimeError("chromadb and sentence-transformers are required for episodic memory") from exc

        self._embedder = SentenceTransformer(self.embedding_model)
        client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = client.get_or_create_collection("episodic_memory")

    def _embed(self, texts: List[str]) -> List[List[float]]:
        assert self._embedder is not None
        vecs = self._embedder.encode(texts, normalize_embeddings=True)
        return vecs.tolist() if hasattr(vecs, "tolist") else list(vecs)

    def load(self) -> None:
        self._cache = {}
        if self.path.exists():
            with self.path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        ep = Episode.from_dict(data)
                        if ep.id:
                            self._cache[ep.id] = ep
                    except Exception as exc:
                        logger.warning(f"Failed to parse episode line: {exc}")
        self._loaded = True

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as handle:
            for ep in self._cache.values():
                handle.write(json.dumps(ep.to_dict()) + "\n")

    def add(
        self,
        *,
        episode_id: str,
        title: str,
        summary: str,
        content: str,
        side: str = "shared",
        tags: Optional[List[str]] = None,
        outcome: str = "unknown",
        trace_ids: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Episode:
        """Add an episode and index it."""
        self._ensure_loaded()
        ep = Episode(
            id=episode_id,
            title=title,
            summary=summary,
            content=content,
            side=side,
            tags=tags or [],
            outcome=outcome,
            trace_ids=trace_ids or [],
            metadata=metadata or {},
        )
        self._cache[ep.id] = ep
        self._index_episode(ep)
        self.save()
        return ep

    def _index_episode(self, episode: Episode) -> None:
        self._ensure_index()
        doc = f"{episode.title}\n\n{episode.summary}\n\n{episode.content}"
        emb = self._embed([doc])[0]
        meta = {
            "id": episode.id,
            "side": episode.side,
            "outcome": episode.outcome,
            "tags": ",".join(episode.tags),
            "created_at": episode.created_at,
        }
        self._collection.upsert(
            ids=[episode.id],
            documents=[doc],
            embeddings=[emb],
            metadatas=[meta],
        )

    def search(self, query: str, k: Optional[int] = None, side: Optional[str] = None) -> Tuple[List[Episode], List[str]]:
        """Semantic search over episodes."""
        self._ensure_loaded()
        self._ensure_index()
        if not query.strip():
            return ([], [])
        emb = self._embed([query.strip()])[0]
        where = None
        if side:
            where = {"side": side}
        res = self._collection.query(
            query_embeddings=[emb],
            n_results=int(k or self.top_k),
            where=where,
            include=["metadatas", "documents", "distances"],
        )
        ids = res.get("ids", [[]])[0]
        episodes: List[Episode] = []
        for eid in ids:
            ep = self._cache.get(eid)
            if ep:
                episodes.append(ep)
        return episodes, ids

    def list(self, limit: int = 100, side: Optional[str] = None) -> List[Episode]:
        self._ensure_loaded()
        items = list(self._cache.values())
        if side:
            items = [e for e in items if e.side == side]
        return items[:limit]

    def delete(self, episode_id: str) -> bool:
        self._ensure_loaded()
        if episode_id not in self._cache:
            return False
        self._cache.pop(episode_id, None)
        if self._collection:
            self._collection.delete(ids=[episode_id])
        self.save()
        return True
