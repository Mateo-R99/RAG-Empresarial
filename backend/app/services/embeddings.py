"""
Servicio de generación de embeddings.
Usa sentence-transformers con singleton para evitar recargar el modelo.
"""

import logging
from typing import Union

from sentence_transformers import SentenceTransformer

from app.config import get_settings

logger = logging.getLogger(__name__)

# Singleton global del modelo de embeddings
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """Obtiene o carga el modelo de embeddings (singleton)."""
    global _model
    if _model is None:
        settings = get_settings()
        logger.info(f"Cargando modelo de embeddings: {settings.embedding_model}")
        _model = SentenceTransformer(settings.embedding_model)
        logger.info(f"Modelo de embeddings cargado exitosamente")
    return _model


class EmbeddingsService:
    """Genera embeddings vectoriales para textos."""

    def __init__(self):
        self.model = _get_model()

    def embed(self, texts: Union[str, list[str]]) -> list[list[float]]:
        """
        Genera embeddings para uno o varios textos.

        Args:
            texts: Un texto o lista de textos

        Returns:
            Lista de vectores (listas de floats)
        """
        if isinstance(texts, str):
            texts = [texts]

        logger.debug(f"Generando embeddings para {len(texts)} textos")
        embeddings = self.model.encode(texts, show_progress_bar=False)
        return embeddings.tolist()

    def embed_query(self, query: str) -> list[float]:
        """
        Genera embedding para una consulta individual.

        Args:
            query: Texto de la consulta

        Returns:
            Vector de embedding
        """
        return self.embed(query)[0]

    @property
    def dimension(self) -> int:
        """Dimensionalidad de los embeddings generados."""
        return self.model.get_sentence_embedding_dimension()
