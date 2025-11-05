"""Simple vector indexes that mimic HNSW and IVF behaviour."""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from .embeddings import Vector, cosine_similarity

LOGGER = logging.getLogger(__name__)


@dataclass
class IndexedVector:
    vector: Vector
    metadata: Dict[str, str]


class VectorIndex:
    """Base class for vector search indexes."""

    def __init__(self, dimension: int, logger: logging.Logger | None = None) -> None:
        self.dimension = dimension
        self._logger = logger or LOGGER

    def add(self, items: Sequence[IndexedVector]) -> None:
        raise NotImplementedError

    def search(self, query: Vector, k: int = 5, **kwargs: object) -> List[Tuple[float, Dict[str, str]]]:
        raise NotImplementedError


class HNSWIndex(VectorIndex):
    """A minimal approximation of an HNSW index."""

    def __init__(
        self,
        dimension: int,
        *,
        ef: int = 32,
        seed: int | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        super().__init__(dimension, logger=logger)
        self.ef = max(ef, 1)
        self._rng = random.Random(seed)
        self._items: List[IndexedVector] = []

    def add(self, items: Sequence[IndexedVector]) -> None:  # type: ignore[override]
        for item in items:
            if len(item.vector) != self.dimension:
                raise ValueError("vector dimension mismatch")
            self._items.append(item)
        self._logger.debug("Added vectors to HNSWIndex", extra={"count": len(items)})

    def search(self, query: Vector, k: int = 5, **_: object) -> List[Tuple[float, Dict[str, str]]]:  # type: ignore[override]
        if len(query) != self.dimension:
            raise ValueError("query dimension mismatch")
        if not self._items:
            return []
        candidates = self._rng.sample(self._items, k=min(len(self._items), self.ef))
        if len(candidates) < len(self._items):
            seen = {id(item) for item in candidates}
            for item in self._items:
                if id(item) not in seen:
                    candidates.append(item)
                    if len(candidates) >= self.ef:
                        break
        scores = [
            (cosine_similarity(query, item.vector), item.metadata)
            for item in candidates
        ]
        scores.sort(key=lambda pair: pair[0], reverse=True)
        top_k = scores[:k]
        self._logger.debug("Performed HNSW search", extra={"k": k, "evaluated": len(candidates)})
        return top_k


class IVFIndex(VectorIndex):
    """Simplified IVF (inverted file) index."""

    def __init__(
        self,
        dimension: int,
        *,
        n_lists: int = 4,
        iterations: int = 5,
        seed: int | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        super().__init__(dimension, logger=logger)
        if n_lists <= 0:
            raise ValueError("n_lists must be positive")
        self.n_lists = n_lists
        self.iterations = max(iterations, 1)
        self._rng = random.Random(seed)
        self._centroids: List[Vector] = []
        self._lists: List[List[IndexedVector]] = []

    def _initialise_centroids(self, data: Sequence[Vector]) -> None:
        indices = list(range(len(data)))
        self._rng.shuffle(indices)
        selected = indices[: self.n_lists]
        self._centroids = [list(data[idx]) for idx in selected]
        self._lists = [[] for _ in range(len(self._centroids))]
        if len(self._centroids) < self.n_lists:
            for _ in range(self.n_lists - len(self._centroids)):
                noise = [self._rng.uniform(-1.0, 1.0) for _ in range(self.dimension)]
                self._centroids.append(noise)
                self._lists.append([])

    def _assign(self, vector: Vector) -> int:
        if not self._centroids:
            raise RuntimeError("Index has not been trained")
        scores = [cosine_similarity(vector, centroid) for centroid in self._centroids]
        return max(range(len(scores)), key=lambda idx: scores[idx])

    def fit(self, data: Sequence[Vector]) -> None:
        if len(data) < self.n_lists:
            raise ValueError("Not enough data to initialise centroids")
        for vector in data:
            if len(vector) != self.dimension:
                raise ValueError("vector dimension mismatch")
        self._initialise_centroids(data)
        for _ in range(self.iterations):
            assignments: List[List[Vector]] = [[] for _ in range(len(self._centroids))]
            for vector in data:
                assignments[self._assign(vector)].append(vector)
            for idx, assigned in enumerate(assignments):
                if not assigned:
                    continue
                centroid = [0.0 for _ in range(self.dimension)]
                for vector in assigned:
                    for dim, value in enumerate(vector):
                        centroid[dim] += value
                count = float(len(assigned))
                centroid = [value / count for value in centroid]
                self._centroids[idx] = centroid
        self._lists = [[] for _ in range(len(self._centroids))]
        self._logger.debug("Trained IVF index", extra={"lists": len(self._lists)})

    def add(self, items: Sequence[IndexedVector]) -> None:  # type: ignore[override]
        if not self._centroids:
            raise RuntimeError("Index must be fit before adding items")
        for item in items:
            if len(item.vector) != self.dimension:
                raise ValueError("vector dimension mismatch")
            bucket = self._assign(item.vector)
            self._lists[bucket].append(item)
        self._logger.debug("Added vectors to IVFIndex", extra={"count": len(items)})

    def search(self, query: Vector, k: int = 5, n_probe: int | None = None, **_: object) -> List[Tuple[float, Dict[str, str]]]:  # type: ignore[override]
        if len(query) != self.dimension:
            raise ValueError("query dimension mismatch")
        if not self._centroids:
            return []
        n_probe = n_probe or min(2, len(self._centroids))
        scores = [cosine_similarity(query, centroid) for centroid in self._centroids]
        ranked = sorted(range(len(scores)), key=lambda idx: scores[idx], reverse=True)[:n_probe]
        candidates: List[IndexedVector] = []
        for idx in ranked:
            candidates.extend(self._lists[idx])
        results = [
            (cosine_similarity(query, item.vector), item.metadata)
            for item in candidates
        ]
        results.sort(key=lambda pair: pair[0], reverse=True)
        top_k = results[:k]
        self._logger.debug(
            "Performed IVF search",
            extra={"k": k, "n_probe": n_probe, "candidates": len(candidates)},
        )
        return top_k


__all__ = [
    "IndexedVector",
    "VectorIndex",
    "HNSWIndex",
    "IVFIndex",
]
