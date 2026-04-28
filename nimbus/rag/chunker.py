"""Chunker simples: divide markdown por parágrafos com overlap configurável."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    source: str


def chunk_markdown(text: str, source: str, overlap: int = 1) -> list[Chunk]:
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
