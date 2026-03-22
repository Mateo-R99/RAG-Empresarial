"""
Tests básicos del pipeline RAG.
Ejecutar: python -m pytest tests/ -v
"""

def test_config_loads():
    """Verifica que la configuración se carga correctamente."""
    from app.config import get_settings
    settings = get_settings()
    assert settings.chunk_size > 0
    assert settings.chunk_overlap >= 0
    assert settings.top_k > 0
    assert settings.temperature >= 0
    assert settings.llm_provider in ("ollama", "openai")


def test_document_processor_pdf():
    """Verifica que el processor soporta PDF."""
    from app.services.document_processor import DocumentProcessor
    processor = DocumentProcessor()
    assert ".pdf" in processor.SUPPORTED_EXTENSIONS


def test_document_processor_docx():
    """Verifica que el processor soporta DOCX."""
    from app.services.document_processor import DocumentProcessor
    processor = DocumentProcessor()
    assert ".docx" in processor.SUPPORTED_EXTENSIONS


def test_chunker_splits_text():
    """Verifica que el chunker divide texto correctamente."""
    from app.services.chunker import Chunker
    chunker = Chunker(chunk_size=100, chunk_overlap=20)
    text = "Este es un texto de prueba. " * 50
    chunks = chunker.split(text, "test.pdf")
    assert len(chunks) > 1
    assert all(c.documento == "test.pdf" for c in chunks)
    assert all(c.chunk_id >= 0 for c in chunks)


def test_embeddings_dimension():
    """Verifica que los embeddings tienen la dimensión esperada."""
    from app.services.embeddings import EmbeddingsService
    service = EmbeddingsService()
    embedding = service.embed_query("texto de prueba")
    assert len(embedding) == 384  # all-MiniLM-L6-v2


def test_embeddings_batch():
    """Verifica que el batch embedding funciona."""
    from app.services.embeddings import EmbeddingsService
    service = EmbeddingsService()
    embeddings = service.embed(["texto uno", "texto dos"])
    assert len(embeddings) == 2
    assert len(embeddings[0]) == len(embeddings[1])
