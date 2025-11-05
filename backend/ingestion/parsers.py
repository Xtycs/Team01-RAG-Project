"""Document parsers for ingestion module.

This module provides light-weight PDF and Word (DOCX) parsers that avoid
heavy optional dependencies so the project can run in constrained
environments.  The parsers expose a common ``BaseParser`` interface and
emit structured ``Document`` objects that downstream components can
consume.

The PDF parser implements a conservative text extraction algorithm that
is sufficient for simple text-based PDFs created during testing.  It
scans the file for text blocks enclosed in parentheses which is how the
PDF text operator encodes literal strings.  While intentionally simple,
this strategy keeps the parser dependency-free and works well for PDFs
produced by the helper utilities in ``tests``.

The DOCX parser leverages the fact that DOCX files are ZIP archives that
store their payload in ``word/document.xml``.  Using the standard library
``zipfile`` and ``xml.etree`` modules we can reliably extract paragraph
content without any third-party packages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import io
import logging
import os
import re
from typing import Dict, Iterable, Optional
from xml.etree import ElementTree
from zipfile import ZipFile


LOGGER = logging.getLogger(__name__)


@dataclass
class Document:
    """Container for parsed document content.

    Attributes
    ----------
    content:
        Full text extracted from the document.  Newlines separate logical
        blocks (e.g. paragraphs or PDF text operations).
    metadata:
        Additional metadata for downstream consumers.  Parsers add the
        ``source_path`` field automatically.
    raw_bytes:
        Raw bytes from the input file.  This is useful for auditing and
        for enabling downstream hashing/deduplication logic without
        reopening the file from disk.
    """

    content: str
    metadata: Dict[str, str] = field(default_factory=dict)
    raw_bytes: bytes = b""


class BaseParser:
    """Base class shared by all document parsers."""

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        self._logger = logger or LOGGER

    def parse(self, file_path: str) -> Document:
        """Parse ``file_path`` and return a :class:`Document` instance.

        Sub-classes implement :meth:`_parse_bytes` to extract structured
        content.  The base implementation takes care of reading the file
        and enriching the metadata with the source path.
        """

        self._logger.debug("Parsing file", extra={"file_path": file_path})
        with open(file_path, "rb") as handle:
            data = handle.read()
        content = self._parse_bytes(data)
        metadata = {"source_path": os.path.abspath(file_path)}
        self._logger.debug(
            "Finished parsing file", extra={"file_path": file_path, "length": len(content)}
        )
        return Document(content=content, metadata=metadata, raw_bytes=data)

    # pylint: disable=unused-argument
    def _parse_bytes(self, data: bytes) -> str:
        """Sub-classes must implement this to return textual content."""

        raise NotImplementedError


class PDFParser(BaseParser):
    """Very small PDF text extractor.

    The extractor reads the binary PDF payload and returns a newline
    joined string of literal text operands (``( … )``) encountered in the
    file.  While this approach does not cover complex PDFs, it is
    adequate for deterministic unit tests and for simple, text-only
    documents.
    """

    _TEXT_PATTERN = re.compile(r"\((?:\\.|[^\\)])*\)")

    def _parse_bytes(self, data: bytes) -> str:  # type: ignore[override]
        self._logger.debug("Extracting text from PDF bytes", extra={"size": len(data)})
        try:
            text = data.decode("latin-1")
        except UnicodeDecodeError as exc:  # pragma: no cover - highly unlikely
            raise ValueError("Unable to decode PDF bytes") from exc

        pieces: Iterable[str] = (
            match.group(0)[1:-1].encode("latin-1").decode("unicode_escape")
            for match in self._TEXT_PATTERN.finditer(text)
        )
        result = "\n".join(piece.strip() for piece in pieces if piece.strip())
        self._logger.debug(
            "Extracted text from PDF", extra={"line_count": len(result.splitlines())}
        )
        return result


class WordParser(BaseParser):
    """Parser for DOCX files built using only the Python standard library."""

    _XML_NAMESPACE = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

    def _parse_bytes(self, data: bytes) -> str:  # type: ignore[override]
        self._logger.debug("Extracting text from DOCX bytes", extra={"size": len(data)})
        with ZipFile(io.BytesIO(data)) as archive:
            with archive.open("word/document.xml") as document_xml:
                tree = ElementTree.parse(document_xml)
        root = tree.getroot()
        paragraphs = []
        for paragraph in root.iter(f"{self._XML_NAMESPACE}p"):
            texts = [
                node.text
                for node in paragraph.iter(f"{self._XML_NAMESPACE}t")
                if node.text
            ]
            if texts:
                paragraphs.append("".join(texts))
        result = "\n".join(paragraphs)
        self._logger.debug(
            "Extracted text from DOCX", extra={"paragraphs": len(paragraphs)}
        )
        return result


__all__ = ["BaseParser", "Document", "PDFParser", "WordParser"]
