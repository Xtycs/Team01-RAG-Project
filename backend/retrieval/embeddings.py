"""Local embedding utilities built without external dependencies."""

from __future__ import annotations

import logging
import math
from collections import Counter
from typing import Iterable, List

LOGGER = logging.getLogger(__name__)

Vector = List[float]


def _zero_vector(dimension: int) -> Vector:
    return [0.0 for _ in range(dimension)]


def _l2_norm(vector: Vector) -> float:
    return math.sqrt(sum(value * value for value in vector))


def _normalise(vector: Vector) -> Vector:
    norm = _l2_norm(vector)
    if norm == 0.0:
        return list(vector)
    return [value / norm for value in vector]


def _add_inplace(target: Vector, source: Vector) -> None:
    for index, value in enumerate(source):
        target[index] += value


def _scale(vector: Vector, scalar: float) -> Vector:
    return [value * scalar for value in vector]


def _mean(vectors: Iterable[Vector]) -> Vector:
    vectors = list(vectors)
    if not vectors:
        raise ValueError("Cannot compute mean of empty sequence")
    dimension = len(vectors[0])
    accumulator = _zero_vector(dimension)
    for vector in vectors:
        if len(vector) != dimension:
            raise ValueError("dimension mismatch in mean computation")
        _add_inplace(accumulator, vector)
    count = float(len(vectors))
    return [value / count for value in accumulator]


class LocalEmbeddingModel:
    """Deterministic character n-gram embedding model."""

    def __init__(
        self,
        *,
        dimension: int = 256,
        ngram_range: tuple[int, int] = (2, 4),
        logger: logging.Logger | None = None,
    ) -> None:
        if dimension <= 0:
            raise ValueError("dimension must be positive")
        if ngram_range[0] <= 0 or ngram_range[1] < ngram_range[0]:
            raise ValueError("invalid ngram_range")
        self.dimension = dimension
        self.ngram_range = ngram_range
        self._logger = logger or LOGGER

    def _generate_ngrams(self, text: str) -> Counter[str]:
        text = text.lower()
        start, end = self.ngram_range
        grams: Counter[str] = Counter()
        for n in range(start, end + 1):
            for index in range(len(text) - n + 1):
                grams[text[index : index + n]] += 1
        self._logger.debug(
            "Generated ngrams", extra={"unique": len(grams), "total": sum(grams.values())}
        )
        return grams

    def embed(self, text: str) -> Vector:
        grams = self._generate_ngrams(text)
        vector = _zero_vector(self.dimension)
        for gram, count in grams.items():
            bucket = hash(gram) % self.dimension
            vector[bucket] += float(count)
        normalised = _normalise(vector)
        self._logger.debug(
            "Created embedding", extra={"dimension": self.dimension, "norm": _l2_norm(normalised)}
        )
        return normalised

    def embed_many(self, texts: Iterable[str]) -> List[Vector]:
        return [self.embed(text) for text in texts]


def cosine_similarity(vec_a: Vector, vec_b: Vector) -> float:
    if len(vec_a) != len(vec_b):
        raise ValueError("dimension mismatch")
    norm_a = _l2_norm(vec_a)
    norm_b = _l2_norm(vec_b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    return dot / (norm_a * norm_b)


__all__ = [
    "LocalEmbeddingModel",
    "cosine_similarity",
    "Vector",
]
