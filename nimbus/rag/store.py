"""Vector store em memória + retrieval por cosine similarity."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

import numpy as np

from nimbus.rag.chunker import Chunk


@dataclass
class RetrievalHit:
    chunk: Chunk
    score: float


class VectorStore:
    def __init__(self, embedder: Any):
        self.embedder = embedder
        self._chunks: list[Chunk] = []
        self._embeddings: np.ndarray | None = None

    def add(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        new_emb = self.embedder.encode([c.text for c in chunks])
        self._chunks.extend(chunks)
        if self._embeddings is None:
            self._embeddings = new_emb
        else:
            self._embeddings = np.vstack([self._embeddings, new_emb])

    def search(self, query: str, top_k: int = 3) -> list[RetrievalHit]:
        if not self._chunks or self._embeddings is None:
            return []
        q = self.embedder.encode([query])[0]
        # embeddings já normalizados → cosine = dot product
        scores = self._embeddings @ q
        top_idx = np.argsort(-scores)[:top_k]
        return [RetrievalHit(chunk=self._chunks[i], score=float(scores[i])) for i in top_idx]
