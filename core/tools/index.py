"""Vector index for tool discovery."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from loguru import logger

from .models import ToolDefinition


@dataclass
class ToolSearchResult:
    name: str
    score: float
    provider: str
    description: str
    tags: List[str]


class ToolIndex:
    """Chroma-backed vector index for tools."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = (config or {}).get("tools", {})
        vector_cfg = (config or {}).get("vector_store", {}) or {}
        self.persist_directory = cfg.get(
            "index_persist_directory",
            "./data/vector_store/tools",
        )
        self.embedding_model = cfg.get(
            "embedding_model",
            vector_cfg.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2"),
        )
        self.collection_name = cfg.get("index_collection", "tool_registry")

        self._client = None
        self._collection = None
        self._embedder = None

        self._init_backends()

    def _init_backends(self) -> None:
        try:
            import chromadb  # type: ignore
            from chromadb.config import Settings  # type: ignore
        except Exception as exc:
            raise RuntimeError("chromadb is required for tool indexing") from exc

        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except Exception as exc:
            raise RuntimeError("sentence-transformers is required for tool indexing") from exc

        self._embedder = SentenceTransformer(self.embedding_model)
        self._client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(self.collection_name)
        logger.info(
            f"ToolIndex ready | dir={self.persist_directory} | embed={self.embedding_model}"
        )

    def _embed(self, texts: List[str]) -> List[List[float]]:
        assert self._embedder is not None
        vecs = self._embedder.encode(texts, normalize_embeddings=True)
        return vecs.tolist() if hasattr(vecs, "tolist") else list(vecs)

    def _build_document(self, tool: ToolDefinition) -> str:
        tags = ", ".join(tool.tags or [])
        provider = tool.provider.value if hasattr(tool.provider, "value") else str(tool.provider)
        return (
            f"Tool: {tool.name}\n"
            f"Provider: {provider}\n"
            f"Description: {tool.description}\n"
            f"Tags: {tags}\n"
        )

    def index_tools(self, tools: Iterable[ToolDefinition]) -> None:
        """Upsert tool definitions into the index."""
        tool_list = list(tools)
        if not tool_list:
            return
        docs = [self._build_document(t) for t in tool_list]
        ids = [t.name for t in tool_list]
        embeddings = self._embed(docs)
        metadatas = []
        for tool in tool_list:
            provider = tool.provider.value if hasattr(tool.provider, "value") else str(tool.provider)
            metadatas.append({
                "name": tool.name,
                "provider": provider,
                "description": tool.description,
                "tags": ",".join(tool.tags or []),
                "enabled": bool(tool.enabled),
                "version": tool.version,
                "risk": tool.risk,
            })
        assert self._collection is not None
        self._collection.upsert(
            ids=ids,
            documents=docs,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def remove(self, tool_name: str) -> None:
        """Remove tool from the index."""
        assert self._collection is not None
        self._collection.delete(ids=[tool_name])

    def search(
        self,
        query: str,
        k: int = 5,
        providers: Optional[List[str]] = None,
    ) -> List[ToolSearchResult]:
        """Search for tools by semantic similarity."""
        if not query.strip():
            return []
        embeddings = self._embed([query.strip()])
        where = None
        if providers:
            where = {"provider": {"$in": providers}}
        assert self._collection is not None
        res = self._collection.query(
            query_embeddings=embeddings,
            n_results=k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        ids = res.get("ids", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[]])[0]
        results: List[ToolSearchResult] = []
        for tool_id, md, dist in zip(ids, metas, dists):
            score = 1.0 - float(dist) if dist is not None else 0.0
            tags = []
            if md and isinstance(md.get("tags"), str):
                tags = [t for t in md.get("tags", "").split(",") if t]
            results.append(
                ToolSearchResult(
                    name=tool_id,
                    score=score,
                    provider=md.get("provider", "") if md else "",
                    description=md.get("description", "") if md else "",
                    tags=tags,
                )
            )
        return results
