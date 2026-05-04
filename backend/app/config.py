"""
Configuración central del sistema RAG.
Usa variables de entorno con valores por defecto sensibles para MVP.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Configuración del sistema cargada desde variables de entorno."""

    # ─── Proveedor LLM ────────────────────────────────────────────
    llm_provider: str = "ollama"  # "ollama" | "openai"

    # ─── Ollama ───────────────────────────────────────────────────
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "llama3"

    # ─── OpenAI (opcional) ────────────────────────────────────────
    openai_api_key: str = ""
    openai_model: str = "gpt-3.5-turbo"

    # ─── Embeddings ───────────────────────────────────────────────
    embedding_model: str = "all-MiniLM-L6-v2"

    # ─── ChromaDB ─────────────────────────────────────────────────
    chroma_host: str = "chroma"
    chroma_port: int = 8000
    chroma_collection: str = "documentos_empresariales"
    chroma_collection_public: str = "documentos_publicos"
    chroma_collection_private: str = "documentos_privados"

    # ─── JWT ──────────────────────────────────────────────────────
    jwt_secret_key: str = "cambiar-en-produccion-clave-super-secreta-2024"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480  # 8 horas

    # ─── Chunking ─────────────────────────────────────────────────
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # ─── Búsqueda y Generación ────────────────────────────────────
    top_k: int = 5
    temperature: float = 0.3

    # ─── Rutas ────────────────────────────────────────────────────
    documents_path: str = "/app/data/documentos"
    query_history_path: str = "/app/data/query_history.json"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Singleton de configuración."""
    return Settings()
