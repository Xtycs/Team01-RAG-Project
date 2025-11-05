"""Deduplication helpers for ingestion pipelines."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Dict, List, Sequence

from .chunking import TextChunk

LOGGER = logging.getLogger(__name__)


@dataclass
class DeduplicatedResult:
    """Result of a deduplication pass."""

    unique_chunks: List[TextChunk]
    duplicates: Dict[str, List[str]]  # hash -> list of chunk ids


def _hash_text(text: str, *, salt: str = "") -> str:
    digest = hashlib.sha256()
    digest.update(salt.encode("utf-8"))
    digest.update(text.encode("utf-8"))
    return digest.hexdigest()


def deduplicate_chunks(
    chunks: Sequence[TextChunk],
    *,
    salt: str = "",
    logger: logging.Logger | None = None,
) -> DeduplicatedResult:
    """Remove duplicate chunks while preserving order.

    ``salt`` can be used to ensure independence between multiple
    deduplication passes (e.g. during experiments).
    """

    active_logger = logger or LOGGER
    seen: Dict[str, TextChunk] = {}
    duplicates: Dict[str, List[str]] = {}
    ordered: List[TextChunk] = []
    for chunk in chunks:
        fingerprint = _hash_text(chunk.text.strip(), salt=salt)
        active_logger.debug(
            "Evaluating chunk for deduplication",
            extra={"chunk_id": chunk.id, "fingerprint": fingerprint[:8]},
        )
        if fingerprint in seen:
            duplicates.setdefault(fingerprint, []).append(str(chunk.id))
            active_logger.debug(
                "Detected duplicate chunk",
                extra={"original_id": seen[fingerprint].id, "duplicate_id": chunk.id},
            )
            continue
        seen[fingerprint] = chunk
        ordered.append(chunk)
    return DeduplicatedResult(unique_chunks=ordered, duplicates=duplicates)


__all__ = ["DeduplicatedResult", "deduplicate_chunks"]
