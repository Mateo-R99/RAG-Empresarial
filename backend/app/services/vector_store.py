"""
Servicio de almacenamiento vectorial con ChromaDB.
Wrapper para operaciones CRUD sobre la base de datos vectorial.
"""

import logging
from typing import Optional
from dataclasses import dataclass

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import get_settings
from app.services.embeddings import EmbeddingsService
from app.services.chunker import Chunk

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Resultado de una búsqueda en el vector store."""
    documento: str
    fragmento: str
    chunk_id: int
    similitud: float
    pagina: Optional[int] = None


class VectorStore:
    """Wrapper sobre ChromaDB para el almacenamiento y búsqueda vectorial."""

    def __init__(self):
        settings = get_settings()
        self.embeddings_service = EmbeddingsService()

        # Conectar a ChromaDB via HTTP
        self.client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
            settings=ChromaSettings(anonymized_telemetry=False)
        )

        # Obtener o crear la colección
        self.collection = self.client.get_or_create_collection(
            name=settings.chroma_collection,
            metadata={"hnsw:space": "cosine"}  # Similitud de coseno
        )

        logger.info(
            f"ChromaDB conectado ({settings.chroma_host}:{settings.chroma_port}), "
            f"colección: {settings.chroma_collection}, "
            f"documentos existentes: {self.collection.count()}"
        )

    def add_documents(self, chunks: list[Chunk]) -> int:
        """
        Añade fragmentos de documento a la base vectorial.

        Args:
            chunks: Lista de fragmentos con metadata

        Returns:
            Número de fragmentos añadidos
        """
        if not chunks:
            return 0

        texts = [chunk.texto for chunk in chunks]
        embeddings = self.embeddings_service.embed(texts)

        ids = [f"{chunks[0].documento}__chunk_{chunk.chunk_id}" for chunk in chunks]
        metadatas = [
            {
                "documento": chunk.documento,
                "chunk_id": chunk.chunk_id,
                "inicio": chunk.inicio,
                "fin": chunk.fin,
                "pagina": chunk.pagina if chunk.pagina else -1,
            }
            for chunk in chunks
        ]

        self.collection.upsert(
            documents=texts,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas,
        )

        logger.info(f"Añadidos {len(chunks)} fragmentos de '{chunks[0].documento}' a ChromaDB")
        return len(chunks)

    def search(self, query: str, top_k: Optional[int] = None) -> list[SearchResult]:
        """
        Búsqueda semántica por similitud de coseno.

        Args:
            query: Texto de búsqueda
            top_k: Número de resultados (usa config por defecto si None)

        Returns:
            Lista de SearchResult ordenados por similitud
        """
        settings = get_settings()
        k = top_k or settings.top_k

        query_embedding = self.embeddings_service.embed_query(query)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(k, self.collection.count()) if self.collection.count() > 0 else k,
            include=["documents", "metadatas", "distances"]
        )

        search_results = []
        if results and results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i]
                # ChromaDB con cosine devuelve distancia, convertir a similitud
                distance = results["distances"][0][i]
                similitud = 1 - distance  # Cosine distance → similarity

                search_results.append(SearchResult(
                    documento=metadata.get("documento", "desconocido"),
                    fragmento=doc,
                    chunk_id=metadata.get("chunk_id", 0),
                    similitud=round(max(0, similitud), 4),
                    pagina=metadata.get("pagina") if metadata.get("pagina", -1) != -1 else None,
                ))

        logger.info(f"Búsqueda: '{query[:50]}...' → {len(search_results)} resultados (top_k={k})")
        return search_results

    def list_documents(self) -> list[dict]:
        """
        Lista todos los documentos indexados con conteo de fragmentos.

        Returns:
            Lista de dicts con nombre del documento y conteo de fragmentos
        """
        all_metadata = self.collection.get(include=["metadatas"])

        doc_counts: dict[str, dict] = {}
        if all_metadata and all_metadata["metadatas"]:
            for meta in all_metadata["metadatas"]:
                doc_name = meta.get("documento", "desconocido")
                if doc_name not in doc_counts:
                    doc_counts[doc_name] = {"nombre": doc_name, "fragmentos": 0}
                doc_counts[doc_name]["fragmentos"] += 1

        return list(doc_counts.values())

    def delete_document(self, documento: str) -> int:
        """
        Elimina todos los fragmentos de un documento.

        Args:
            documento: Nombre del documento a eliminar

        Returns:
            Número de fragmentos eliminados
        """
        # Obtener IDs de los fragmentos del documento
        results = self.collection.get(
            where={"documento": documento},
            include=[]
        )

        if results and results["ids"]:
            self.collection.delete(ids=results["ids"])
            count = len(results["ids"])
            logger.info(f"Eliminados {count} fragmentos de '{documento}'")
            return count

        return 0

    def is_connected(self) -> bool:
        """Verifica la conexión con ChromaDB."""
        try:
            self.client.heartbeat()
            return True
        except Exception:
            return False
