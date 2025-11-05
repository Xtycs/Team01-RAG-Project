from __future__ import annotations

import json
import time
import urllib.request

import math
import pytest

from backend.retrieval.api import LocalRetrievalAPI, RetrievalRequestHandler
from backend.retrieval.embeddings import LocalEmbeddingModel
from backend.retrieval.index import HNSWIndex, IVFIndex, IndexedVector


@pytest.fixture(autouse=True)
def reset_state() -> None:
    # Ensure each test starts with a fresh handler state.
    RetrievalRequestHandler.state = RetrievalRequestHandler.state.__class__()


def test_embedding_model_produces_normalised_vectors() -> None:
    model = LocalEmbeddingModel(dimension=32)
    vector = model.embed("example text")
    norm = math.sqrt(sum(value * value for value in vector))
    assert math.isclose(norm, 1.0, rel_tol=1e-6)


def test_hnsw_index_returns_expected_document() -> None:
    model = LocalEmbeddingModel(dimension=32)
    index = HNSWIndex(dimension=32, ef=10, seed=123)
    documents = [
        "the quick brown fox",
        "lorem ipsum dolor",
        "retrieval augmented generation",
    ]
    vectors = model.embed_many(documents)
    index.add(
        [
            IndexedVector(vector=vector, metadata={"text": text})
            for vector, text in zip(vectors, documents)
        ]
    )
    query = model.embed("quick brown animal")
    results = index.search(query, k=1)
    assert results[0][1]["text"] == "the quick brown fox"


def test_ivf_index_end_to_end() -> None:
    model = LocalEmbeddingModel(dimension=32)
    documents = [f"document {i}" for i in range(10)]
    vectors = model.embed_many(documents)
    index = IVFIndex(dimension=32, n_lists=3, iterations=2, seed=42)
    index.fit(vectors)
    index.add(
        [
            IndexedVector(vector=vector, metadata={"text": text})
            for vector, text in zip(vectors, documents)
        ]
    )
    query = model.embed("document 1")
    results = index.search(query, k=3, n_probe=2)
    assert any(result[1]["text"] == "document 1" for result in results)


def test_retrieval_api_round_trip() -> None:
    api = LocalRetrievalAPI()
    api.start()
    try:
        base_url = f"http://{api.host}:{api.port}"
        configure_request = urllib.request.Request(
            f"{base_url}/configure",
            data=json.dumps({"index": "HNSWIndex", "dimension": 32}).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(configure_request) as response:
            assert response.status == 200
        doc_request = urllib.request.Request(
            f"{base_url}/documents",
            data=json.dumps({"text": "local rag systems", "metadata": {"id": "1"}}).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(doc_request) as response:
            assert response.status == 201
        query_request = urllib.request.Request(
            f"{base_url}/query",
            data=json.dumps({"text": "rag"}).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(query_request) as response:
            body = json.loads(response.read())
        assert body["results"]
        assert body["results"][0]["metadata"]["id"] == "1"
    finally:
        api.stop()
