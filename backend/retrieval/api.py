"""HTTP API for local retrieval operations."""

from __future__ import annotations

import json
import logging
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
from typing import Dict, List, Optional
from urllib.parse import urlparse

from .embeddings import LocalEmbeddingModel, Vector
from .index import HNSWIndex, IVFIndex, IndexedVector

LOGGER = logging.getLogger(__name__)


class RetrievalState:
    """Mutable state shared between HTTP handlers."""

    def __init__(self) -> None:
        self.embedding_model = LocalEmbeddingModel()
        self.index: Optional[HNSWIndex | IVFIndex] = None
        self._lock = threading.Lock()

    def ensure_index(self, kind: str, dimension: int) -> None:
        with self._lock:
            if self.index and self.index.dimension == dimension and self.index.__class__.__name__ == kind:
                return
            self.embedding_model = LocalEmbeddingModel(dimension=dimension)
            if kind == "HNSWIndex":
                self.index = HNSWIndex(dimension)
            elif kind == "IVFIndex":
                self.index = IVFIndex(dimension)
            else:
                raise ValueError(f"Unsupported index type: {kind}")
            LOGGER.debug("Created new index", extra={"type": kind, "dimension": dimension})

    def add_vector(self, vector: Vector, metadata: Dict[str, str]) -> None:
        if not self.index:
            raise RuntimeError("Index has not been initialised")
        self.index.add([IndexedVector(vector=vector, metadata=metadata)])

    def search(self, vector: Vector, k: int, **kwargs: object) -> List[Dict[str, object]]:
        if not self.index:
            return []
        results = self.index.search(vector, k=k, **kwargs)
        payload: List[Dict[str, object]] = []
        for score, metadata in results:
            payload.append({"score": float(score), "metadata": metadata})
        return payload


def _json_response(handler: BaseHTTPRequestHandler, payload: Dict[str, object], status: int = HTTPStatus.OK) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class RetrievalRequestHandler(BaseHTTPRequestHandler):
    """HTTP handler that routes requests to the retrieval backend."""

    state = RetrievalState()

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler naming convention
        parsed = urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length) if content_length else b"{}"
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            _json_response(self, {"error": "Invalid JSON"}, status=HTTPStatus.BAD_REQUEST)
            return

        if parsed.path == "/configure":
            kind = payload.get("index", "HNSWIndex")
            dimension = int(payload.get("dimension", 256))
            try:
                self.state.ensure_index(kind, dimension)
            except ValueError as exc:  # pragma: no cover - defensive
                _json_response(self, {"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            _json_response(self, {"status": "ok"})
            return

        if parsed.path == "/documents":
            metadata = payload.get("metadata", {})
            text = payload.get("text", "")
            if not isinstance(metadata, dict) or not isinstance(text, str):
                _json_response(self, {"error": "Invalid payload"}, status=HTTPStatus.BAD_REQUEST)
                return
            vector = self.state.embedding_model.embed(text)
            try:
                self.state.add_vector(vector, {**{k: str(v) for k, v in metadata.items()}, "text": text})
            except RuntimeError as exc:
                _json_response(self, {"error": str(exc)}, status=HTTPStatus.CONFLICT)
                return
            _json_response(self, {"status": "ok"}, status=HTTPStatus.CREATED)
            return

        if parsed.path == "/query":
            text = payload.get("text", "")
            k = int(payload.get("k", 5))
            extra = {}
            if "n_probe" in payload:
                extra["n_probe"] = int(payload["n_probe"])
            vector = self.state.embedding_model.embed(text)
            results = self.state.search(vector, k=k, **extra)
            _json_response(self, {"results": results})
            return

        _json_response(self, {"error": "Unsupported endpoint"}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003 - signature defined upstream
        LOGGER.info("HTTP %s - %s", format, args)


class LocalRetrievalAPI:
    """Small helper that manages the HTTP server lifecycle."""

    def __init__(self, host: str = "127.0.0.1", port: int = 0) -> None:
        self.host = host
        self.port = port
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._server:
            return
        self._server = ThreadingHTTPServer((self.host, self.port), RetrievalRequestHandler)
        self.port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        LOGGER.debug("Started retrieval API", extra={"host": self.host, "port": self.port})

    def stop(self) -> None:
        if not self._server:
            return
        self._server.shutdown()
        if self._thread:
            self._thread.join(timeout=1)
        self._server.server_close()
        self._server = None
        self._thread = None
        LOGGER.debug("Stopped retrieval API")


__all__ = ["LocalRetrievalAPI", "RetrievalRequestHandler", "RetrievalState"]
