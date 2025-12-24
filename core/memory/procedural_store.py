"""Procedural memory playbooks (ACE-style bullets).

Design goals:
 - Keep procedural knowledge separate from factual RAG documents.
 - Maintain separate collections per hemisphere (left/right) plus a shared
   consensus collection.
 - Store many small, itemized bullets; avoid rewriting monolithic summaries.

This module uses Chroma for persistence and Sentence-Transformers for
embeddings (both already listed in requirements.txt).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

from loguru import logger


@dataclass
class ProceduralBullet:
    id: str
    text: str
    side: str  # left|right|shared
    type: str = "heuristic"  # tool_rule|heuristic|checklist|pitfall|template|example
    tags: List[str] = None
    status: str = "active"  # active|quarantined|deprecated
    confidence: float = 0.5
    helpful_count: int = 0
    harmful_count: int = 0
    created_at: str = ""
    last_used_at: str = ""
    source_trace_id: str = ""

    def to_metadata(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "side": self.side,
            "type": self.type,
            "tags": ",".join(self.tags or []),
            "status": self.status,
            "confidence": float(self.confidence),
            "helpful_count": int(self.helpful_count),
            "harmful_count": int(self.harmful_count),
            "created_at": self.created_at,
            "last_used_at": self.last_used_at,
            "source_trace_id": self.source_trace_id,
        }


class ProceduralMemoryStore:
    """Persistent vector store for procedural playbooks.

    One *physical* Chroma persistence directory, with three collections:
    - procedural_left
    - procedural_right
    - procedural_shared
    """

    COLLECTIONS = {
        "left": "procedural_left",
        "right": "procedural_right",
        "shared": "procedural_shared",
    }

    def __init__(self, config: Dict[str, Any]):
        cfg = (config or {}).get("procedural_memory", {})
        self.enabled = bool(cfg.get("enabled", True))
        self.persist_directory = cfg.get("persist_directory", "./data/memory/procedural")
        self.embedding_model = cfg.get(
            "embedding_model",
            (config.get("vector_store", {}) or {}).get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2"),
        )

        # Learning policy
        self.cross_teaching = cfg.get("cross_teaching", "shared_only")  # shared_only|suggestions
        self.promote_threshold = int(cfg.get("promote_threshold", 3))
        self.quarantine_threshold = int(cfg.get("quarantine_threshold", 2))

        self.k_left = int(cfg.get("k_left", 8))
        self.k_right = int(cfg.get("k_right", 16))
        self.k_shared = int(cfg.get("k_shared", 5))

        self._client = None
        self._collections = {}
        self._embedder = None

        if not self.enabled:
            logger.warning("ProceduralMemoryStore disabled by config")
            return

        self._init_backends()

    def _init_backends(self) -> None:
        try:
            import chromadb  # type: ignore
            from chromadb.config import Settings  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "chromadb is required for procedural_memory (see requirements.txt)"
            ) from e

        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "sentence-transformers is required for procedural_memory (see requirements.txt)"
            ) from e

        self._embedder = SentenceTransformer(self.embedding_model)
        self._client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(anonymized_telemetry=False),
        )

        for side, cname in self.COLLECTIONS.items():
            self._collections[side] = self._client.get_or_create_collection(name=cname)

        logger.info(
            f"🧩 ProceduralMemoryStore ready | dir={self.persist_directory} | embed={self.embedding_model}"
        )

    @staticmethod
    def _now() -> str:
        return datetime.utcnow().isoformat(timespec="seconds") + "Z"

    def _embed(self, texts: List[str]) -> List[List[float]]:
        assert self._embedder is not None
        vecs = self._embedder.encode(texts, normalize_embeddings=True)
        return vecs.tolist() if hasattr(vecs, "tolist") else list(vecs)

    def add_bullet(
        self,
        *,
        side: str,
        text: str,
        bullet_type: str = "heuristic",
        tags: Optional[List[str]] = None,
        status: str = "quarantined",
        confidence: float = 0.5,
        source_trace_id: str = "",
        bullet_id: Optional[str] = None,
    ) -> ProceduralBullet:
        """Add a new bullet as a single vector entry."""

        if not self.enabled:
            raise RuntimeError("procedural_memory is disabled")

        side = side.lower().strip()
        if side not in self.COLLECTIONS:
            raise ValueError(f"Invalid side '{side}'")

        now = self._now()
        bullet_id = bullet_id or f"pb_{side}_{int(datetime.utcnow().timestamp()*1000)}"

        b = ProceduralBullet(
            id=bullet_id,
            text=text.strip(),
            side=side,
            type=bullet_type,
            tags=tags or [],
            status=status,
            confidence=float(confidence),
            helpful_count=0,
            harmful_count=0,
            created_at=now,
            last_used_at="",
            source_trace_id=source_trace_id,
        )

        emb = self._embed([b.text])[0]
        col = self._collections[side]
        col.upsert(ids=[b.id], documents=[b.text], embeddings=[emb], metadatas=[b.to_metadata()])
        return b

    def query(
        self,
        *,
        side: str,
        query_text: str,
        tags: Optional[List[str]] = None,
        k: Optional[int] = None,
        min_confidence: Optional[float] = None,
        include_shared: bool = True,
    ) -> Tuple[List[ProceduralBullet], List[str]]:
        """Retrieve bullets for a hemisphere.

        Returns (bullets, used_ids).
        """
        if not self.enabled:
            return ([], [])

        side = side.lower().strip()
        if side not in self.COLLECTIONS:
            raise ValueError(f"Invalid side '{side}'")

        k = int(k or (self.k_left if side == "left" else self.k_right))
        qemb = self._embed([query_text.strip()])[0]

        bullets: List[ProceduralBullet] = []
        used_ids: List[str] = []

        def _fetch_from(s: str, top_k: int, min_conf: Optional[float], tag_filter: Optional[List[str]]):
            col = self._collections[s]
            where = {"status": {"$ne": "deprecated"}}

            # Chroma doesn't support list-contains well across backends; we store tags as comma string.
            # We keep tag filtering lightweight here; stronger filtering can be done post-query.
            res = col.query(
                query_embeddings=[qemb],
                n_results=top_k,
                where=where,
                include=["documents", "metadatas", "distances"],
            )
            ids = res.get("ids", [[]])[0]  # Chroma always returns ids even if not in include
            docs = res.get("documents", [[]])[0]
            metas = res.get("metadatas", [[]])[0]
            dists = res.get("distances", [[]])[0]

            out: List[ProceduralBullet] = []
            for i, doc, md, dist in zip(ids, docs, metas, dists):
                try:
                    conf = float(md.get("confidence", 0.5))
                except Exception:
                    conf = 0.5

                if min_conf is not None and conf < min_conf:
                    continue

                # Post-filter tags if provided
                if tag_filter:
                    md_tags = (md.get("tags") or "").split(",") if isinstance(md.get("tags"), str) else []
                    md_tags = [t for t in md_tags if t]
                    if not any(t in md_tags for t in tag_filter):
                        continue

                out.append(
                    ProceduralBullet(
                        id=i,
                        text=doc,
                        side=s,
                        type=md.get("type", "heuristic"),
                        tags=[t for t in (md.get("tags") or "").split(",") if t],
                        status=md.get("status", "active"),
                        confidence=float(md.get("confidence", 0.5)),
                        helpful_count=int(md.get("helpful_count", 0)),
                        harmful_count=int(md.get("harmful_count", 0)),
                        created_at=md.get("created_at", ""),
                        last_used_at=md.get("last_used_at", ""),
                        source_trace_id=md.get("source_trace_id", ""),
                    )
                )

            # Sort by: (confidence + helpful - harmful) then similarity proxy
            out.sort(
                key=lambda b: (
                    b.confidence + 0.05 * b.helpful_count - 0.1 * b.harmful_count,
                ),
                reverse=True,
            )
            return out

        # Hemisphere collection
        min_confidence = min_confidence
        bullets.extend(_fetch_from(side, k, min_confidence, tags))

        # Shared collection (small, high-confidence)
        if include_shared:
            shared_k = self.k_shared
            shared_min = 0.8 if min_confidence is None else max(min_confidence, 0.8)
            bullets.extend(_fetch_from("shared", shared_k, shared_min, tags))

        # Deduplicate by text
        seen = set()
        deduped: List[ProceduralBullet] = []
        for b in bullets:
            t = b.text.strip().lower()
            if t in seen:
                continue
            seen.add(t)
            deduped.append(b)

        # Record usage timestamp
        for b in deduped[:k]:
            used_ids.append(b.id)
            self._touch(b)

        return (deduped[: k + (self.k_shared if include_shared else 0)], used_ids)

    def _touch(self, bullet: ProceduralBullet) -> None:
        """Update last_used_at for a bullet."""
        try:
            col = self._collections[bullet.side]
            now = self._now()
            # Fetch existing metadata
            res = col.get(ids=[bullet.id], include=["metadatas", "documents"])
            md = (res.get("metadatas") or [{}])[0] or {}
            doc = (res.get("documents") or [bullet.text])[0]
            md["last_used_at"] = now
            col.upsert(ids=[bullet.id], documents=[doc], metadatas=[md])
        except Exception as e:
            logger.debug(f"procedural_memory touch failed: {e}")

    def record_outcome(self, bullet_ids: List[str], *, helpful: bool) -> None:
        """Increment helpful/harmful counters for bullets that were actually used.

        NOTE: This is intentionally *not* tied 1:1 with consciousness ticks. You call this
        when you have an outcome signal (test pass/fail, tool success/failure, user feedback).
        """
        if not self.enabled or not bullet_ids:
            return
        for bid in bullet_ids:
            self._increment(bid, helpful=helpful)

    def _increment(self, bullet_id: str, *, helpful: bool) -> None:
        # Bullet IDs include side prefix but we still need to locate which collection.
        for side in ("left", "right", "shared"):
            col = self._collections[side]
            got = col.get(ids=[bullet_id], include=["metadatas", "documents"])
            if not got.get("ids"):
                continue
            md = (got.get("metadatas") or [{}])[0] or {}
            doc = (got.get("documents") or [""])[0]

            if helpful:
                md["helpful_count"] = int(md.get("helpful_count", 0)) + 1
            else:
                md["harmful_count"] = int(md.get("harmful_count", 0)) + 1

            # Auto-promote from quarantined to active when confirmed
            status = md.get("status", "active")
            if status == "quarantined" and int(md.get("helpful_count", 0)) >= self.quarantine_threshold and int(md.get("harmful_count", 0)) == 0:
                md["status"] = "active"

            col.upsert(ids=[bullet_id], documents=[doc], metadatas=[md])

            # Consider promotion to shared if coming from left/right and policy allows
            if side in ("left", "right"):
                self._maybe_promote_to_shared(side, doc, md)
            return

    def _maybe_promote_to_shared(self, origin_side: str, doc: str, md: Dict[str, Any]) -> None:
        if self.cross_teaching not in ("shared_only", "suggestions"):
            return
        if int(md.get("helpful_count", 0)) < self.promote_threshold:
            return
        if int(md.get("harmful_count", 0)) > 0:
            return
        if md.get("status") != "active":
            return

        # Upsert into shared collection (id stable but namespaced)
        shared_id = f"shared__{md.get('id', '')}"
        now = self._now()
        shared_md = dict(md)
        shared_md["id"] = shared_id
        shared_md["side"] = "shared"
        shared_md["created_at"] = shared_md.get("created_at") or now
        shared_md["source_trace_id"] = shared_md.get("source_trace_id") or f"promoted_from:{origin_side}"
        shared_md["confidence"] = max(float(shared_md.get("confidence", 0.5)), 0.8)
        shared_md["status"] = "active"

        emb = self._embed([doc])[0]
        self._collections["shared"].upsert(
            ids=[shared_id],
            documents=[doc],
            embeddings=[emb],
            metadatas=[shared_md],
        )
