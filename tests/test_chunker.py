from nimbus.rag.chunker import Chunk, chunk_markdown


def test_chunk_markdown_basico():
    text = "Parágrafo um.\n\nParágrafo dois.\n\nParágrafo três."
    chunks = chunk_markdown(text, source="x.md", overlap=0)
    assert len(chunks) == 3
    assert chunks[0].text == "Parágrafo um."
    assert all(isinstance(c, Chunk) for c in chunks)
    assert all(c.source == "x.md" for c in chunks)


def test_chunk_markdown_pula_paragrafos_vazios():
    text = "A.\n\n\n\nB."
    chunks = chunk_markdown(text, source="x.md", overlap=0)
    assert len(chunks) == 2


def test_chunk_markdown_overlap():
    text = "A.\n\nB.\n\nC.\n\nD."
    chunks = chunk_markdown(text, source="x.md", overlap=1)
    assert chunks[1].text.startswith("A.")  # incluiu o anterior
    assert "B." in chunks[1].text
