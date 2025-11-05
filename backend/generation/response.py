"""Response generation utilities."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Iterable, List

from .fusion import ContextSnippet, ContextFusion

LOGGER = logging.getLogger(__name__)


@dataclass
class Citation:
    """Metadata for a cited snippet."""

    text: str
    source: str
    score: float


@dataclass
class GeneratedResponse:
    """Full response payload returned to the caller."""

    answer: str
    citations: List[Citation]


class ResponseGenerator:
    """Generates responses backed by fused context snippets."""

    def __init__(self, fusion: ContextFusion | None = None, logger: logging.Logger | None = None) -> None:
        self.fusion = fusion or ContextFusion()
        self._logger = logger or LOGGER

    def _build_answer(self, question: str, snippets: Iterable[ContextSnippet]) -> str:
        parts = [f"Question: {question}"]
        for index, snippet in enumerate(snippets, start=1):
            parts.append(f"Snippet {index}: {snippet.content}")
        parts.append("Answer: Based on the retrieved information, the question can be addressed using the cited snippets above.")
        return "\n".join(parts)

    def _build_citations(self, snippets: Iterable[ContextSnippet]) -> List[Citation]:
        citations = [
            Citation(
                text=snippet.content,
                source=snippet.metadata.get("source", "unknown"),
                score=snippet.score,
            )
            for snippet in snippets
        ]
        self._logger.debug("Constructed citations", extra={"count": len(citations)})
        return citations

    def generate(self, question: str, snippets: Iterable[ContextSnippet]) -> GeneratedResponse:
        fused = self.fusion.fuse(list(snippets))
        self._logger.debug("Generating response", extra={"snippets": len(fused)})
        answer = self._build_answer(question, fused)
        citations = self._build_citations(fused)
        return GeneratedResponse(answer=answer, citations=citations)


__all__ = ["Citation", "GeneratedResponse", "ResponseGenerator"]
