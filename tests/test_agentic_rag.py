import pytest
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import FakeEmbeddings

from integrations.rag.agentic_rag import AgenticRAG


@pytest.fixture
def anyio_backend():
    return "asyncio"


class FakeLLM:
    """Minimal async LLM stub."""

    class _Resp:
        def __init__(self, content):
            self.content = content

    async def ainvoke(self, prompt):
        text = str(prompt)
        if "Does this context" in text:
            return self._Resp("SUFFICIENT context")
        if "Should we search again" in text:
            return self._Resp("SUFFICIENT")
        return self._Resp("Answer: synthetic response")


@pytest.mark.anyio("asyncio")
async def test_agentic_rag_single_and_agentic(tmp_path):
    # Build in-memory vector store with fake embeddings
    embeddings = FakeEmbeddings(size=16)
    vectorstore = FAISS.from_texts(
        texts=[
            "The capital of France is Paris.",
            "The capital of Germany is Berlin.",
            "Paris has landmarks like the Eiffel Tower.",
        ],
        embedding=embeddings,
    )

    config = {
        "rag": {"top_k": 2, "max_iterations": 3, "chunk_size": 64, "chunk_overlap": 8},
        "vector_store": {},
    }
    rag = AgenticRAG(config, FakeLLM(), vectorstore=vectorstore)

    # Single-pass retrieval
    single = await rag.retrieve("What is the capital of France?", mode="single")
    assert "answer" in single
    assert single["sources"]

    # Agentic retrieval (iterative)
    agentic = await rag.retrieve("Tell me about Paris", mode="agentic")
    assert agentic["iterations"] >= 1
    assert agentic["sources"]
