"""Context fusion utilities."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import List, Sequence

LOGGER = logging.getLogger(__name__)


@dataclass
class ContextSnippet:
    """Small unit of retrieved context."""

    content: str
    metadata: dict[str, str]
    score: float


class ContextFusion:
    """Fuse retrieved snippets into a consolidated context window."""

    def __init__(self, max_tokens: int = 512, logger: logging.Logger | None = None) -> None:
        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        self.max_tokens = max_tokens
        self._logger = logger or LOGGER

    @staticmethod
    def _token_estimate(text: str) -> int:
        # Simple heuristic: number of whitespace separated tokens.
        return max(1, len(text.split()))

    def fuse(self, snippets: Sequence[ContextSnippet]) -> List[ContextSnippet]:
        """Return a curated list of snippets that respects ``max_tokens``."""

        ordered = sorted(snippets, key=lambda snippet: snippet.score, reverse=True)
        budget = self.max_tokens
        fused: List[ContextSnippet] = []
        for snippet in ordered:
            cost = self._token_estimate(snippet.content)
            if cost > budget:
                self._logger.debug(
                    "Skipping snippet - exceeds budget",
                    extra={"snippet_score": snippet.score, "cost": cost, "budget": budget},
                )
                continue
            fused.append(snippet)
            budget -= cost
            self._logger.debug(
                "Selected snippet",
                extra={"remaining_budget": budget, "score": snippet.score},
            )
            if budget <= 0:
                break
        return fused


__all__ = ["ContextSnippet", "ContextFusion"]
