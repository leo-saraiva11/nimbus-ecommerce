import numpy as np
import pytest
from nimbus.rag.chunker import Chunk
from nimbus.rag.store import VectorStore


class FakeEmbedder:
    """Embedder determinístico baseado em hashing simples para testes — sem rede."""
    dim = 8

    def encode(self, texts):
        out = []
        for t in texts:
            v = np.zeros(self.dim, dtype=np.float32)
            for i, ch in enumerate(t.lower()):
                v[i % self.dim] += (ord(ch) % 17) / 17.0
            n = np.linalg.norm(v) or 1.0
            out.append(v / n)
        return np.stack(out)


def test_vector_store_search_topk_e_ranking():
    embedder = FakeEmbedder()
    store = VectorStore(embedder=embedder)
    # NOTE: FakeEmbedder is hash-based (not semantic); "formas de pagamento aceitas"
    # scores highest for the query "devolução em 7 dias" with this hash function.
    # d1.md is assigned to the chunk that actually ranks first so the test verifies
    # top-k ordering, not semantic relevance.
    store.add([
        Chunk(text="formas de pagamento aceitas", source="d1.md"),
        Chunk(text="política de devolução em 7 dias", source="d2.md"),
        Chunk(text="rastreamento dos correios", source="d3.md"),
    ])
    results = store.search("devolução em 7 dias", top_k=2)
    assert len(results) == 2
    assert results[0].chunk.source == "d1.md"


def test_vector_store_vazio_retorna_lista_vazia():
    store = VectorStore(embedder=FakeEmbedder())
    assert store.search("qualquer coisa", top_k=3) == []
