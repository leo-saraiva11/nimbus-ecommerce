from nimbus.rag.chunker import Chunk, chunk_markdown, whole_document


def test_whole_document_retorna_um_chunk_com_texto_completo():
    text = "# Título\n\nParágrafo 1.\n\nParágrafo 2."
    chunks = whole_document(text, source="x.md")
    assert len(chunks) == 1
    assert chunks[0].source == "x.md"
    assert "Título" in chunks[0].text
    assert "Parágrafo 1." in chunks[0].text
    assert "Parágrafo 2." in chunks[0].text


def test_whole_document_descarta_arquivo_vazio():
    assert whole_document("", "x.md") == []
    assert whole_document("   \n\n  ", "x.md") == []


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
