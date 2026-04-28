"""Estratégias de chunking. Para corpus pequeno, ``whole_document`` é o padrão."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    source: str


def whole_document(text: str, source: str) -> list[Chunk]:
    """Trata cada documento como 1 único chunk.

    Indicado para corpus pequeno (docs curtos, ~500-2000 tokens cada): o
    embedding do documento inteiro casa muito melhor com a pergunta do que
    chunks pequenos do título ou de um parágrafo isolado, e o modelo recebe
    o contexto completo de uma só vez (sem precisar de top_k alto).
    """
    text = text.strip()
    if not text:
        return []
    return [Chunk(text=text, source=source)]


def chunk_markdown(text: str, source: str, overlap: int = 1) -> list[Chunk]:
    """Chunking por parágrafo com overlap. Útil quando os documentos são
    grandes o suficiente pra justificar fragmentação. Para o corpus atual
    do projeto preferimos ``whole_document`` — esta função fica disponível
    para casos em que o corpus crescer."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []
    chunks: list[Chunk] = []
    for i, p in enumerate(paragraphs):
        if overlap > 0 and i > 0:
            start = max(0, i - overlap)
            joined = "\n\n".join(paragraphs[start:i + 1])
            chunks.append(Chunk(text=joined, source=source))
        else:
            chunks.append(Chunk(text=p, source=source))
    return chunks
