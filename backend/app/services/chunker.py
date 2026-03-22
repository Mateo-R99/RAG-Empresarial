"""
Servicio de chunking (división de texto en fragmentos).
Usa RecursiveCharacterTextSplitter para respetar la estructura del texto.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """Un fragmento de texto con su metadata."""
    texto: str
    chunk_id: int
    documento: str
    inicio: int
    fin: int
    pagina: Optional[int] = None


class Chunker:
    """Divide documentos en fragmentos configurables."""

    def __init__(self, chunk_size: Optional[int] = None, chunk_overlap: Optional[int] = None):
        settings = get_settings()
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", ", ", " ", ""],
            is_separator_regex=False,
        )

    def split(self, texto: str, documento: str, paginas_detalle: list[dict] = None) -> list[Chunk]:
        """
        Divide un texto en fragmentos con metadata.

        Args:
            texto: Texto completo del documento
            documento: Nombre del documento origen
            paginas_detalle: Lista de {"pagina": N, "texto": "..."} para mapeo de páginas

        Returns:
            Lista de Chunks con metadata
        """
        documents = self.splitter.create_documents(
            texts=[texto],
            metadatas=[{"documento": documento}]
        )

        chunks = []
        current_pos = 0

        for i, doc in enumerate(documents):
            chunk_text = doc.page_content
            start_pos = texto.find(chunk_text, current_pos)
            if start_pos == -1:
                start_pos = current_pos

            # Determinar la página si hay detalle disponible
            pagina = self._find_page(chunk_text, paginas_detalle) if paginas_detalle else None

            chunks.append(Chunk(
                texto=chunk_text,
                chunk_id=i,
                documento=documento,
                inicio=start_pos,
                fin=start_pos + len(chunk_text),
                pagina=pagina,
            ))

            current_pos = start_pos + len(chunk_text) - self.chunk_overlap

        logger.info(
            f"Documento '{documento}' dividido en {len(chunks)} fragmentos "
            f"(chunk_size={self.chunk_size}, overlap={self.chunk_overlap})"
        )

        return chunks

    def _find_page(self, chunk_text: str, paginas_detalle: list[dict]) -> Optional[int]:
        """Busca en qué página del documento original cae el chunk."""
        if not paginas_detalle:
            return None

        # Buscar la página que contiene la mayor parte del chunk
        best_match = None
        best_overlap = 0

        for page_info in paginas_detalle:
            page_text = page_info["texto"]
            # Calcular superposición usando los primeros 100 caracteres del chunk
            sample = chunk_text[:100]
            if sample in page_text:
                overlap = len(sample)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_match = page_info["pagina"]

        return best_match
