from __future__ import annotations

from backend.generation.fusion import ContextFusion, ContextSnippet
from backend.generation.response import ResponseGenerator


def test_context_fusion_respects_token_budget() -> None:
    snippets = [
        ContextSnippet(content="short context", metadata={"source": "a"}, score=0.9),
        ContextSnippet(content="this is a considerably longer context snippet", metadata={"source": "b"}, score=0.8),
    ]
    fusion = ContextFusion(max_tokens=3)
    fused = fusion.fuse(snippets)
    assert len(fused) == 1
    assert fused[0].metadata["source"] == "a"


def test_response_generator_produces_citations() -> None:
    snippets = [
        ContextSnippet(content="answer part", metadata={"source": "doc1"}, score=0.7),
        ContextSnippet(content="additional", metadata={"source": "doc2"}, score=0.6),
    ]
    generator = ResponseGenerator()
    response = generator.generate("What is RAG?", snippets)
    assert "Question: What is RAG?" in response.answer
    assert response.citations[0].source == "doc1"
    assert len(response.citations) <= len(snippets)
