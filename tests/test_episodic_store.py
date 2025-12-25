import pytest


def test_episodic_store_add_and_list(tmp_path):
    chroma = pytest.importorskip("chromadb")
    SentenceTransformer = pytest.importorskip("sentence_transformers").SentenceTransformer

    config = {
        "episodic_memory": {
            "path": str(tmp_path / "episodes.jsonl"),
            "persist_directory": str(tmp_path / "vectordb"),
            "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
            "top_k": 3,
        }
    }

    from core.memory.episodic_store import EpisodicStore

    store = EpisodicStore(config)
    store.load()

    ep = store.add(
        episode_id="ep1",
        title="Test Episode",
        summary="We tested the system",
        content="Detailed content about the test episode.",
        side="shared",
        tags=["test", "episode"],
        outcome="success",
    )

    assert ep.id == "ep1"
    listed = store.list()
    assert listed and listed[0].title == "Test Episode"

    results, ids = store.search("test episode", k=1)
    assert results
    assert results[0].id == "ep1"
