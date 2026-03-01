# Agentic RAG

An iterative retrieval module with refinement and synthesis, now using plain prompts (no LangChain chaining) and injectable vector stores for easy testing.

## Usage

```python
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import FakeEmbeddings
from integrations.rag.agentic_rag import AgenticRAG

# Fake LLM for illustration
class FakeLLM:
    class _Resp:
        def __init__(self, content): self.content = content
    async def ainvoke(self, prompt):
        return self._Resp("Answer: example")

embeddings = FakeEmbeddings(size=16)
vectorstore = FAISS.from_texts(["Doc about Paris", "Doc about Berlin"], embedding=embeddings)

rag = AgenticRAG(
    {"rag": {"top_k": 2, "max_iterations": 3}},
    FakeLLM(),
    vectorstore=vectorstore,
)

# Add documents (optional)
rag.add_documents(["Extra doc about France"])

# Retrieve
result = await rag.retrieve("What is Paris known for?", mode="agentic")
print(result["answer"])
```

## Notes
- Vector store and embeddings are injectable (use FAISS + FakeEmbeddings for tests).
- Prompts are plain strings; any async LLM with `ainvoke(prompt)` returning an object with `content` works.
- Logging is ASCII-only; no special characters.

## Tests
- `tests/test_agentic_rag.py` covers single and iterative modes with a fake LLM and in-memory FAISS store.
