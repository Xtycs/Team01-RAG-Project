"""High-level HTTP API gateway that orchestrates the RAG pipeline.

The gateway exposes a very small JSON-based interface that frontends can use
for configuring the retrieval backend, uploading documents, and issuing
questions.  It stitches together the ingestion, retrieval, and generation
modules that already exist in the codebase while keeping the runtime
requirements limited to the Python standard library.
"""

from __future__ import annotations

import json
import logging
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
from typing import Dict, Iterable, List, Optional, Sequence

from backend.generation.fusion import ContextFusion, ContextSnippet
from backend.generation.response import GeneratedResponse, ResponseGenerator
from backend.ingestion.chunking import TextChunk, chunk_text
from backend.ingestion.deduplication import DeduplicatedResult, deduplicate_chunks
from backend.retrieval.embeddings import LocalEmbeddingModel
from backend.retrieval.index import HNSWIndex, IVFIndex, IndexedVector, VectorIndex

LOGGER = logging.getLogger(__name__)


def _stringify_metadata(metadata: Dict[str, object]) -> Dict[str, str]:
    """Convert metadata values to strings so they remain JSON serialisable."""

    return {key: str(value) for key, value in metadata.items()}


class PipelineState:
    """Mutable application state that coordinates ingestion, retrieval, and generation."""

    def __init__(self) -> None:
        self.embedding_model = LocalEmbeddingModel()
        self.index: Optional[VectorIndex] = None
        self.generator = ResponseGenerator()
        self.chunk_size = 400
        self.overlap = 40
        self._lock = threading.RLock()
        self._ingested_documents: List[Dict[str, str]] = []
        self._chunk_counter = 0

    def _initialise_index(self, index_type: str, dimension: int, params: Dict[str, object]) -> VectorIndex:
        index_type = index_type.lower()
        if index_type == "hnsw":
            ef = int(params.get("ef", 32))
            return HNSWIndex(dimension, ef=ef)
        if index_type == "ivf":
            n_lists = int(params.get("n_lists", 4))
            iterations = int(params.get("iterations", 5))
            return IVFIndex(dimension, n_lists=n_lists, iterations=iterations)
        raise ValueError(f"Unsupported index type: {index_type}")

    def configure(
        self,
        *,
        index_type: str = "hnsw",
        dimension: int = 256,
        chunk_size: int = 400,
        overlap: int = 40,
        generator_max_tokens: int | None = None,
        index_params: Optional[Dict[str, object]] = None,
    ) -> Dict[str, object]:
        """Configure the pipeline and reset previously ingested state."""

        params = index_params or {}
        with self._lock:
            LOGGER.debug(
                "Configuring pipeline",
                extra={
                    "index_type": index_type,
                    "dimension": dimension,
                    "chunk_size": chunk_size,
                    "overlap": overlap,
                    "index_params": params,
                },
            )
            self.embedding_model = LocalEmbeddingModel(dimension=dimension)
            self.index = self._initialise_index(index_type, dimension, params)
            if generator_max_tokens is not None:
                self.generator = ResponseGenerator(fusion=ContextFusion(max_tokens=generator_max_tokens))
            else:
                self.generator = ResponseGenerator()
            self.chunk_size = chunk_size
            self.overlap = overlap
            self._ingested_documents.clear()
            self._chunk_counter = 0
        return {
            "status": "configured",
            "index": index_type,
            "dimension": dimension,
            "chunk_size": chunk_size,
            "overlap": overlap,
            "index_params": params,
            "generator_max_tokens": generator_max_tokens,
        }

    def _prepare_chunks(
        self,
        document: Dict[str, object],
        *,
        document_id: int,
    ) -> Sequence[TextChunk]:
        content = document.get("content", "")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Document content must be a non-empty string")
        metadata = document.get("metadata", {})
        if not isinstance(metadata, dict):
            raise ValueError("Document metadata must be a dictionary")
        label = str(document.get("name", metadata.get("source", f"document-{document_id}")))
        chunk_metadata = {"document_id": str(document_id), "source": label}
        chunk_metadata.update(_stringify_metadata(metadata))
        chunks = chunk_text(
            content,
            chunk_size=self.chunk_size,
            overlap=self.overlap,
            metadata=chunk_metadata,
        )
        return chunks

    def _embed_chunks(self, chunks: Sequence[TextChunk]) -> List[IndexedVector]:
        vectors: List[IndexedVector] = []
        for chunk in chunks:
            metadata = dict(chunk.metadata)
            metadata.setdefault("chunk_id", str(self._chunk_counter))
            metadata.setdefault("text", chunk.text)
            metadata = _stringify_metadata(metadata)
            vector = self.embedding_model.embed(chunk.text)
            vectors.append(IndexedVector(vector=vector, metadata=metadata))
            self._chunk_counter += 1
        return vectors

    def ingest(self, documents: Sequence[Dict[str, object]]) -> Dict[str, object]:
        with self._lock:
            if self.index is None:
                raise RuntimeError("Pipeline has not been configured")
            summaries: List[Dict[str, object]] = []
            total_chunks = 0
            duplicates_summary: Dict[str, List[str]] = {}
            for doc_index, document in enumerate(documents, start=1):
                chunks = self._prepare_chunks(document, document_id=len(self._ingested_documents) + doc_index)
                dedup_result: DeduplicatedResult = deduplicate_chunks(chunks)
                indexed_vectors = self._embed_chunks(dedup_result.unique_chunks)
                if isinstance(self.index, IVFIndex) and not getattr(self.index, "_centroids", []):
                    # ``fit`` expects the raw vectors.
                    raw_vectors = [item.vector for item in indexed_vectors]
                    if len(raw_vectors) < self.index.n_lists:
                        raise ValueError(
                            "Not enough unique chunks to initialise IVF index; "
                            f"expected at least {self.index.n_lists}, received {len(raw_vectors)}"
                        )
                    self.index.fit(raw_vectors)
                self.index.add(indexed_vectors)
                total_chunks += len(indexed_vectors)
                duplicates_summary.update(dedup_result.duplicates)
                summary = {
                    "name": document.get("name"),
                    "metadata": _stringify_metadata(document.get("metadata", {})),
                    "chunks": len(indexed_vectors),
                }
                summaries.append(summary)
                self._ingested_documents.append({
                    "label": summary.get("name") or summary["metadata"].get("source", "unknown"),
                    "chunks": str(summary["chunks"]),
                })
            LOGGER.debug(
                "Ingested documents",
                extra={"documents": len(documents), "chunks": total_chunks},
            )
            return {
                "status": "ingested",
                "documents": summaries,
                "chunks": total_chunks,
                "duplicates": duplicates_summary,
            }

    def _build_snippets(self, results: Iterable[tuple[float, Dict[str, str]]]) -> List[ContextSnippet]:
        snippets: List[ContextSnippet] = []
        for score, metadata in results:
            text = metadata.get("text", "")
            if not text:
                continue
            snippet_metadata = dict(metadata)
            snippet_metadata.setdefault("source", metadata.get("source_path", metadata.get("source", "unknown")))
            snippets.append(ContextSnippet(content=text, metadata=snippet_metadata, score=score))
        return snippets

    def query(self, question: str, *, k: int = 5, retrieval_params: Optional[Dict[str, object]] = None) -> Dict[str, object]:
        with self._lock:
            if self.index is None:
                raise RuntimeError("Pipeline has not been configured")
            if not question.strip():
                raise ValueError("Question must be a non-empty string")
            retrieval_params = retrieval_params or {}
            vector = self.embedding_model.embed(question)
            results = self.index.search(vector, k=k, **retrieval_params)
            snippets = self._build_snippets(results)
            generated: GeneratedResponse = self.generator.generate(question, snippets)
            LOGGER.debug("Generated response", extra={"citations": len(generated.citations)})
            return {
                "status": "answered",
                "answer": generated.answer,
                "citations": [
                    {"text": citation.text, "source": citation.source, "score": citation.score}
                    for citation in generated.citations
                ],
                "snippets": [
                    {
                        "content": snippet.content,
                        "score": snippet.score,
                        "metadata": snippet.metadata,
                    }
                    for snippet in snippets
                ],
            }


def _json_response(handler: BaseHTTPRequestHandler, payload: Dict[str, object], *, status: int = HTTPStatus.OK) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.send_header("Access-Control-Allow-Methods", "OPTIONS, POST")
    handler.end_headers()
    handler.wfile.write(body)


class RAGGatewayHandler(BaseHTTPRequestHandler):
    """HTTP handler that exposes the pipeline state via JSON endpoints."""

    state: PipelineState = PipelineState()

    def do_OPTIONS(self) -> None:  # noqa: N802 - required signature
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "OPTIONS, POST")
        self.end_headers()

    def _parse_body(self) -> Dict[str, object]:
        length = int(self.headers.get("Content-Length", "0"))
        data = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON payload")

    def do_POST(self) -> None:  # noqa: N802 - required signature
        try:
            payload = self._parse_body()
        except ValueError as exc:
            _json_response(self, {"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        try:
            if self.path == "/setup":
                response = self.state.configure(
                    index_type=str(payload.get("index", "hnsw")),
                    dimension=int(payload.get("dimension", 256)),
                    chunk_size=int(payload.get("chunk_size", 400)),
                    overlap=int(payload.get("overlap", 40)),
                    generator_max_tokens=(
                        int(payload["generator_max_tokens"]) if payload.get("generator_max_tokens") else None
                    ),
                    index_params=payload.get("index_params"),
                )
                _json_response(self, response)
                return
            if self.path == "/ingest":
                documents = payload.get("documents", [])
                if not isinstance(documents, list):
                    raise ValueError("documents must be a list")
                response = self.state.ingest(documents)
                _json_response(self, response, status=HTTPStatus.CREATED)
                return
            if self.path == "/query":
                question = str(payload.get("question", ""))
                top_k = int(payload.get("k", 5))
                retrieval_params = payload.get("retrieval", {})
                if retrieval_params and not isinstance(retrieval_params, dict):
                    raise ValueError("retrieval parameters must be a dictionary")
                response = self.state.query(question, k=top_k, retrieval_params=retrieval_params)
                _json_response(self, response)
                return
        except ValueError as exc:
            _json_response(self, {"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        except RuntimeError as exc:
            _json_response(self, {"error": str(exc)}, status=HTTPStatus.CONFLICT)
            return

        _json_response(self, {"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003 - upstream signature
        LOGGER.info("HTTP %s - %s", format, args)


class RAGAPIServer:
    """Convenience wrapper that manages the HTTP server lifecycle."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8000, state: PipelineState | None = None) -> None:
        self.host = host
        self.port = port
        self.state = state or PipelineState()
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._server:
            return
        handler = type(
            "ConfiguredRAGGatewayHandler",
            (RAGGatewayHandler,),
            {"state": self.state},
        )
        self._server = ThreadingHTTPServer((self.host, self.port), handler)
        self.port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        LOGGER.info("Started RAG API server", extra={"host": self.host, "port": self.port})

    def stop(self) -> None:
        if not self._server:
            return
        self._server.shutdown()
        if self._thread:
            self._thread.join(timeout=1)
        self._server.server_close()
        self._server = None
        self._thread = None
        LOGGER.info("Stopped RAG API server")


__all__ = ["PipelineState", "RAGAPIServer", "RAGGatewayHandler"]
