from __future__ import annotations

import tempfile
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree

from backend.ingestion.chunking import chunk_text
from backend.ingestion.deduplication import deduplicate_chunks
from backend.ingestion.parsers import PDFParser, WordParser


def _create_fake_pdf(path: Path, text: str) -> None:
    content = f"%PDF-1.1\n1 0 obj<<>>endobj\nBT ({text}) Tj ET\n%%EOF"
    path.write_bytes(content.encode("latin-1"))


def _create_docx(path: Path, paragraphs: list[str]) -> None:
    document = ElementTree.Element(
        "w:document",
        {"xmlns:w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"},
    )
    body = ElementTree.SubElement(document, "w:body")
    for paragraph in paragraphs:
        p = ElementTree.SubElement(body, "w:p")
        r = ElementTree.SubElement(p, "w:r")
        t = ElementTree.SubElement(r, "w:t")
        t.text = paragraph
    xml_bytes = ElementTree.tostring(document, encoding="utf-8")
    with ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types></Types>")
        archive.writestr("word/document.xml", xml_bytes)


def test_pdf_parser_extracts_text(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.pdf"
    _create_fake_pdf(file_path, "Hello PDF")
    parser = PDFParser()
    document = parser.parse(str(file_path))
    assert "Hello PDF" in document.content
    assert document.metadata["source_path"].endswith("sample.pdf")


def test_word_parser_extracts_text(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.docx"
    _create_docx(file_path, ["First paragraph", "Second paragraph"])
    parser = WordParser()
    document = parser.parse(str(file_path))
    assert "First paragraph" in document.content
    assert "Second paragraph" in document.content


def test_chunking_and_deduplication_workflow() -> None:
    text = "Lorem ipsum dolor sit amet consectetur adipiscing elit."
    chunks = chunk_text(text, chunk_size=20, overlap=5)
    # Duplicate the chunks intentionally.
    duplicated = chunks + chunks
    result = deduplicate_chunks(duplicated)
    assert len(result.unique_chunks) == len(chunks)
    assert result.duplicates  # Duplicates should be tracked
