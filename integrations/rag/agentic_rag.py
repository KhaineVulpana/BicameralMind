"""Agentic RAG: Iterative Retrieval with Self-Checking."""
import asyncio
from typing import List, Dict, Any, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from loguru import logger


class AgenticRAG:
    """
    Agentic RAG System:
    - Multi-pass retrieval driven by model reasoning
    - Query refinement and reformulation
    - Coverage and confidence checking
    - Goal-directed search with stopping criteria
    """
    
    def __init__(
        self,
        config: Dict[str, Any],
        llm_client,
        *,
        llm_fast=None,
        llm_slow=None,
        vectorstore=None,
        splitter: Optional[RecursiveCharacterTextSplitter] = None,
        embeddings=None,
    ):
        self.config = config.get("rag", {}) if isinstance(config, dict) else {}
        self.llm = llm_client
        self.llm_fast = llm_fast or llm_client
        self.llm_slow = llm_slow or llm_client

        # Vector store setup (allow injection for tests)
        if vectorstore is not None:
            self.vectorstore = vectorstore
        else:
            embed_model = (config.get("vector_store", {}) or {}).get(
                "embedding_model", "sentence-transformers/all-MiniLM-L6-v2"
            )
            embeddings = embeddings or HuggingFaceEmbeddings(model_name=embed_model)
            persist_dir = (config.get("vector_store", {}) or {}).get(
                "persist_directory", "./data/vector_store"
            )
            self.vectorstore = Chroma(
                persist_directory=persist_dir,
                embedding_function=embeddings,
            )

        # Text splitter
        self.splitter = splitter or RecursiveCharacterTextSplitter(
            chunk_size=self.config.get("chunk_size", 512),
            chunk_overlap=self.config.get("chunk_overlap", 50),
        )
    
    async def retrieve(self, query: str, mode: str = "agentic") -> Dict[str, Any]:
        """
        Retrieve relevant information
        mode: 'agentic' for iterative or 'single' for one-shot
        """
        
        if mode == "single":
            return await self._single_pass_retrieve(query)

        if self._should_skip_agentic():
            result = await self._single_pass_retrieve(query)
            result["skipped_agentic"] = True
            result["skip_reason"] = "insufficient_docs"
            return result

        return await self._agentic_retrieve(query)
    
    async def _single_pass_retrieve(self, query: str) -> Dict[str, Any]:
        """Traditional RAG: single retrieval pass"""
        
        if self.vectorstore is None:
            raise RuntimeError("Vector store is not initialized")

        docs = self.vectorstore.similarity_search(
            query,
            k=self.config.get("top_k", 5)
        )
        
        context = "\n\n".join([doc.page_content for doc in docs])
        
        prompt = self._format_synthesis_prompt(query, context)
        llm = self.llm_slow or self.llm
        response = await llm.ainvoke(prompt)
        
        return {
            "answer": response.content if hasattr(response, 'content') else str(response),
            "sources": docs,
            "iterations": 1
        }
    
    async def _agentic_retrieve(self, query: str) -> Dict[str, Any]:
        """Agentic RAG: iterative retrieval with refinement"""
        
        max_iterations = self.config.get("max_iterations", 5)
        all_retrieved = []
        iteration = 0
        current_query = query

        if self.vectorstore is None:
            raise RuntimeError("Vector store is not initialized")
        
        logger.info(f"Agentic RAG: Starting retrieval for '{query}'")
        
        while iteration < max_iterations:
            iteration += 1
            
            # Retrieve
            docs = self.vectorstore.similarity_search(
                current_query,
                k=self.config.get("top_k", 5)
            )
            
            all_retrieved.extend(docs)
            
            # Check coverage
            context = "\n\n".join([doc.page_content for doc in all_retrieved])
            coverage = await self._assess_coverage(query, context, iteration)
            
            logger.debug(f"Iteration {iteration}: Coverage {coverage['score']:.2f}")
            
            # Decide: continue or stop?
            if coverage["sufficient"] or iteration >= max_iterations:
                logger.info(f"Coverage sufficient after {iteration} iterations")
                break
            
            # Refine query
            refined = await self._refine_query(query, context, coverage)
            
            if refined["action"] == "SUFFICIENT":
                break
            
            current_query = refined.get("new_query", query)
            logger.debug(f"  Refined query: {current_query}")
        
        # Synthesize final answer
        final_context = "\n\n".join([doc.page_content for doc in all_retrieved])
        prompt = self._format_synthesis_prompt(query, final_context)
        llm = self.llm_slow or self.llm
        response = await llm.ainvoke(prompt)
        
        return {
            "answer": response.content if hasattr(response, 'content') else str(response),
            "sources": all_retrieved,
            "iterations": iteration,
            "final_query": current_query
        }
    
    async def _assess_coverage(self, query: str, context: str, iteration: int) -> Dict[str, Any]:
        """Assess if retrieved context sufficiently covers the query"""
        
        prompt = self._format_coverage_prompt(query, context)
        llm = self.llm_fast or self.llm
        response = await llm.ainvoke(prompt)
        result = response.content if hasattr(response, "content") else str(response)

        sufficient = "SUFFICIENT" in result and "INSUFFICIENT" not in result.upper()
        
        return {
            "sufficient": sufficient,
            "score": 0.9 if sufficient else 0.3,
            "reason": result
        }
    
    async def _refine_query(self, original: str, context: str, coverage: Dict) -> Dict[str, Any]:
        """Refine query to improve retrieval"""
        
        prompt = self._format_refine_prompt(
            original=original,
            retrieved=context[:300],
            coverage=coverage.get("reason", ""),
        )
        llm = self.llm_fast or self.llm
        response = await llm.ainvoke(prompt)
        result = response.content if hasattr(response, "content") else str(response)
        
        if "SUFFICIENT" in result:
            return {"action": "SUFFICIENT"}
        
        # Extract refined query
        lines = result.strip().split('\n')
        new_query = original
        for line in lines:
            if line.strip() and not line.startswith(("Query:", "Retrieved:", "Coverage:")):
                new_query = line.strip()
                break
        
        return {
            "action": "REFINE",
            "new_query": new_query
        }
    
    def add_documents(self, documents: List[str], metadata: Optional[List[Dict]] = None):
        """Add documents to vector store"""
        
        if self.vectorstore is None:
            raise RuntimeError("Vector store is not initialized")

        splits = []
        for doc in documents or []:
            splits.extend(self.splitter.split_text(doc))

        if not splits:
            return

        metadatas = metadata or [{} for _ in splits]
        if len(metadatas) != len(splits):
            if len(metadatas) < len(splits):
                metadatas = metadatas + ([{}] * (len(splits) - len(metadatas)))
            else:
                metadatas = metadatas[: len(splits)]

        self.vectorstore.add_texts(splits, metadatas=metadatas)

        logger.info(f"Added {len(splits)} chunks to knowledge base")

    def _vectorstore_count(self) -> Optional[int]:
        store = self.vectorstore
        if store is None:
            return 0
        if hasattr(store, "_collection"):
            try:
                return int(store._collection.count())
            except Exception:
                pass
        if hasattr(store, "index") and hasattr(store.index, "ntotal"):
            try:
                return int(store.index.ntotal)
            except Exception:
                pass
        if hasattr(store, "index_to_docstore_id"):
            try:
                return len(store.index_to_docstore_id)
            except Exception:
                pass
        try:
            return len(store)
        except Exception:
            return None

    def _should_skip_agentic(self) -> bool:
        count = self._vectorstore_count()
        if count is None:
            return False

        top_k = int(self.config.get("top_k", 5) or 5)
        min_docs = self.config.get("min_docs_for_agentic")
        if min_docs is None:
            min_docs = max(top_k * 2, top_k + 1)
        try:
            min_docs = int(min_docs)
        except (TypeError, ValueError):
            min_docs = max(top_k * 2, top_k + 1)

        if count < min_docs:
            logger.info(
                "Agentic RAG: skipping iterative retrieval (docs=%s < min_docs_for_agentic=%s)",
                count,
                min_docs,
            )
            return True

        return False

    # Prompt helpers
    def _format_synthesis_prompt(self, query: str, context: str) -> str:
        return f"""Synthesize retrieved information to answer the query.

Query: {query}
Context:
{context}

Answer:"""

    def _format_refine_prompt(self, original: str, retrieved: str, coverage: str) -> str:
        return f"""Analyze the query and retrieved context. If gaps exist, reformulate the query to get better results.

Query: {original}
Retrieved: {retrieved}
Coverage: {coverage}

Should we search again? If yes, provide refined query. If no, say SUFFICIENT."""

    def _format_coverage_prompt(self, query: str, context: str) -> str:
        return f"""Does this context sufficiently answer the query?

Query: {query}
Context: {context[:500]}...

Respond: SUFFICIENT or INSUFFICIENT [reason]"""
