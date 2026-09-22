"""Local embedding service using sentence-transformers."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    pass


class EmbeddingService:
    """Generates embeddings locally using sentence-transformers.

    Falls back to a simple hash-based embedding if the model isn't available.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self._model_name = model_name
        self._model = None
        self._lock = threading.Lock()
        self._dimension = 384  # Default for all-MiniLM-L6-v2

    def _load_model(self) -> None:
        if self._model is not None:
            return
        with self._lock:
            if self._model is not None:
                return
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self._model_name)
                self._dimension = self._model.get_sentence_embedding_dimension()
            except Exception:
                self._model = "fallback"

    @property
    def dimension(self) -> int:
        self._load_model()
        if self._model == "fallback":
            return 256
        return self._dimension  # type: ignore[return-value]

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts into vectors."""
        self._load_model()
        if self._model == "fallback":
            return [self._fallback_embed(t) for t in texts]
        embeddings = self._model.encode(texts, show_progress_bar=False)  # type: ignore[union-attr]
        return [e.tolist() for e in embeddings]

    def embed_one(self, text: str) -> list[float]:
        """Embed a single text."""
        return self.embed([text])[0]

    def _fallback_embed(self, text: str) -> list[float]:
        """Simple hash-based fallback when sentence-transformers isn't available."""
        import hashlib
        h = hashlib.sha256(text.lower().encode()).digest()
        vec = np.frombuffer(h, dtype=np.uint8).astype(np.float32)
        # Pad or truncate to fixed size
        target = 256
        if len(vec) >= target:
            vec = vec[:target]
        else:
            vec = np.pad(vec, (0, target - len(vec)))
        vec = vec / (np.linalg.norm(vec) + 1e-8)
        return vec.tolist()
