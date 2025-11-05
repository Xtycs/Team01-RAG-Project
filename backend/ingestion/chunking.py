"""Utilities for chunking parsed documents.

Chunking is implemented as a generator-friendly function that yields
:class:`TextChunk` instances, allowing downstream code to stream chunks
without loading everything into memory.  Hooks for custom logging are
provided so the ingestion pipeline can surface detailed telemetry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Dict, Iterator, List, Optional


LOGGER = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """Represents a chunked section of text."""

    id: int
    text: str
    metadata: Dict[str, str] = field(default_factory=dict)


def chunk_text(
    text: str,
    *,
    chunk_size: int = 512,
    overlap: int = 64,
    metadata: Optional[Dict[str, str]] = None,
    logger: Optional[logging.Logger] = None,
) -> List[TextChunk]:
    """Split ``text`` into overlapping windows.

    Parameters
    ----------
    text:
        Source text to split.
    chunk_size:
        Maximum characters per chunk.
    overlap:
        Number of characters to overlap between consecutive chunks.
    metadata:
        Optional metadata that is attached to every chunk.
    logger:
        Custom logger used for debug information.  Defaults to the module
        level logger.
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0:
        raise ValueError("overlap must be non-negative")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    active_logger = logger or LOGGER
    meta = metadata or {}
    chunks: List[TextChunk] = []
    start = 0
    index = 0
    text_length = len(text)
    active_logger.debug(
        "Starting chunking", extra={"chunk_size": chunk_size, "overlap": overlap, "length": text_length}
    )
    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk_text_value = text[start:end]
        chunk_metadata = dict(meta)
        chunk_metadata.update({"start": str(start), "end": str(end)})
        chunks.append(TextChunk(id=index, text=chunk_text_value, metadata=chunk_metadata))
        active_logger.debug(
            "Created chunk",
            extra={"chunk_id": index, "start": start, "end": end, "length": len(chunk_text_value)},
        )
        if end == text_length:
            break
        start = end - overlap
        index += 1
    return chunks


def stream_chunks(
    text: str,
    *,
    chunk_size: int = 512,
    overlap: int = 64,
    metadata: Optional[Dict[str, str]] = None,
    logger: Optional[logging.Logger] = None,
) -> Iterator[TextChunk]:
    """Yield chunks one-by-one.

    This is a thin wrapper around :func:`chunk_text` that yields the
    resulting chunks lazily.
    """

    for chunk in chunk_text(
        text,
        chunk_size=chunk_size,
        overlap=overlap,
        metadata=metadata,
        logger=logger,
    ):
        yield chunk


__all__ = ["TextChunk", "chunk_text", "stream_chunks"]
