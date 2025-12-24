"""Agentic RAG: Iterative Retrieval with Self-Checking"""
import asyncio
from typing import List, Dict, Any, Optional
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.prompts import ChatPromptTemplate
from loguru import logger


class AgenticRAG:
    """
    Agentic RAG System:
    - Multi-pass retrieval driven by model reasoning
    - Query refinement and reformulation
    - Coverage and confidence checking
    - Goal-directed search with stopping criteria
    """
    
    def __init__(self, config: Dict[str, Any], llm_client):
        self.config = config.get("rag", {})
        self.llm = llm_client
        
        # Vector store setup
        embeddings = HuggingFaceEmbeddings(
            model_name=config.get("vector_store", {}).get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2")
        )
        
        persist_dir = config.get("vector_store", {}).get("persist_directory", "./data/vector_store")
        
        self.vectorstore = Chroma(
            persist_directory=persist_dir,
            embedding_function=embeddings
        )
        
        # Text splitter
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.get("chunk_size", 512),
            chunk_overlap=self.config.get("chunk_overlap", 50)
        )
        
        # RAG templates
        self.query_refine_template = ChatPromptTemplate.from_messages([
            ("system", "Analyze the query and retrieved context. If gaps exist, reformulate the query to get better results."),
            ("human", """Query: {query}
Retrieved: {retrieved}
Coverage: {coverage}

Should we search again? If yes, provide refined query. If no, say SUFFICIENT.""")
        ])
        
        self.synthesis_template = ChatPromptTemplate.from_messages([
            ("system", "Synthesize retrieved information to answer the query."),
            ("human", """Query: {query}
Context: {context}

Answer:""")
        ])
    
    async def retrieve(self, query: str, mode: str = "agentic") -> Dict[str, Any]:
        """
        Retrieve relevant information
        mode: 'agentic' for iterative or 'single' for one-shot
        """
        
        if mode == "single":
            return await self._single_pass_retrieve(query)
        else:
            return await self._agentic_retrieve(query)
    
    async def _single_pass_retrieve(self, query: str) -> Dict[str, Any]:
        """Traditional RAG: single retrieval pass"""
        
        docs = self.vectorstore.similarity_search(
            query,
            k=self.config.get("top_k", 5)
        )
        
        context = "\n\n".join([doc.page_content for doc in docs])
        
        # Synthesize answer
        chain = self.synthesis_template | self.llm
        response = await chain.ainvoke({
            "query": query,
            "context": context
        })
        
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
        
        logger.info(f"🔍 Agentic RAG: Starting retrieval for '{query}'")
        
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
            
            logger.debug(f"  Iteration {iteration}: Coverage {coverage['score']:.2f}")
            
            # Decide: continue or stop?
            if coverage["sufficient"] or iteration >= max_iterations:
                logger.info(f"✓ Coverage sufficient after {iteration} iterations")
                break
            
            # Refine query
            refined = await self._refine_query(query, context, coverage)
            
            if refined["action"] == "SUFFICIENT":
                break
            
            current_query = refined.get("new_query", query)
            logger.debug(f"  Refined query: {current_query}")
        
        # Synthesize final answer
        final_context = "\n\n".join([doc.page_content for doc in all_retrieved])
        
        chain = self.synthesis_template | self.llm
        response = await chain.ainvoke({
            "query": query,
            "context": final_context
        })
        
        return {
            "answer": response.content if hasattr(response, 'content') else str(response),
            "sources": all_retrieved,
            "iterations": iteration,
            "final_query": current_query
        }
    
    async def _assess_coverage(self, query: str, context: str, iteration: int) -> Dict[str, Any]:
        """Assess if retrieved context sufficiently covers the query"""
        
        # Simple heuristic: check if context mentions key terms
        # More sophisticated: use LLM to judge coverage
        
        prompt = f"""Does this context sufficiently answer the query?
Query: {query}
Context: {context[:500]}...

Respond: SUFFICIENT or INSUFFICIENT [reason]"""
        
        response = await self.llm.ainvoke(prompt)
        result = response.content if hasattr(response, 'content') else str(response)
        
        sufficient = "SUFFICIENT" in result and "INSUFFICIENT" not in result
        
        return {
            "sufficient": sufficient,
            "score": 0.9 if sufficient else 0.3,
            "reason": result
        }
    
    async def _refine_query(self, original: str, context: str, coverage: Dict) -> Dict[str, Any]:
        """Refine query to improve retrieval"""
        
        chain = self.query_refine_template | self.llm
        response = await chain.ainvoke({
            "query": original,
            "retrieved": context[:300],
            "coverage": coverage["reason"]
        })
        
        result = response.content if hasattr(response, 'content') else str(response)
        
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
        
        # Split documents
        splits = []
        for doc in documents:
            splits.extend(self.splitter.split_text(doc))
        
        # Add to vectorstore
        self.vectorstore.add_texts(splits, metadatas=metadata)
        
        logger.info(f"Added {len(splits)} chunks to knowledge base")
