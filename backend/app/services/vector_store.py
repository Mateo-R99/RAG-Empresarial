"""
Servicio de almacenamiento vectorial con ChromaDB.
Soporta colecciones duales (pública/privada) con búsqueda según rol.
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
    coleccion: Optional[str] = None


class VectorStore:
    """Wrapper sobre ChromaDB para el almacenamiento y búsqueda vectorial."""

    def __init__(self, collection_name: Optional[str] = None):
        settings = get_settings()
        self.embeddings_service = EmbeddingsService()

        # Conectar a ChromaDB via HTTP
        self.client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
            settings=ChromaSettings(anonymized_telemetry=False)
        )

        # Determinar nombre de colección
        self._collection_name = collection_name or settings.chroma_collection_public

        # Obtener o crear la colección
        self.collection = self.client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"}  # Similitud de coseno
        )

        logger.info(
            f"ChromaDB conectado ({settings.chroma_host}:{settings.chroma_port}), "
            f"colección: {self._collection_name}, "
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

        logger.info(f"Añadidos {len(chunks)} fragmentos de '{chunks[0].documento}' a colección '{self._collection_name}'")
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
                    coleccion=self._collection_name,
                ))

        logger.info(f"Búsqueda [{self._collection_name}]: '{query[:50]}...' → {len(search_results)} resultados (top_k={k})")
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
                    doc_counts[doc_name] = {
                        "nombre": doc_name,
                        "fragmentos": 0,
                        "coleccion": self._collection_name,
                    }
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
            logger.info(f"Eliminados {count} fragmentos de '{documento}' en colección '{self._collection_name}'")
            return count

        return 0

    def get_total_count(self) -> int:
        """Retorna el total de fragmentos en la colección."""
        return self.collection.count()

    def is_connected(self) -> bool:
        """Verifica la conexión con ChromaDB."""
        try:
            self.client.heartbeat()
            return True
        except Exception:
            return False


class MultiVectorStore:
    """
    Busca en múltiples colecciones y combina resultados.
    Usado para el rol 'gerente' que accede a documentos públicos y privados.
    """

    def __init__(self):
        settings = get_settings()
        self.vs_public = VectorStore(collection_name=settings.chroma_collection_public)
        self.vs_private = VectorStore(collection_name=settings.chroma_collection_private)

    def search(self, query: str, top_k: Optional[int] = None) -> list[SearchResult]:
        """
        Busca en ambas colecciones y combina resultados por similitud.

        Args:
            query: Texto de búsqueda
            top_k: Número total de resultados deseados

        Returns:
            Lista combinada de SearchResult ordenados por similitud
        """
        settings = get_settings()
        k = top_k or settings.top_k

        # Buscar en ambas colecciones (pedir más para luego filtrar)
        results_pub = self.vs_public.search(query, top_k=k)
        results_priv = self.vs_private.search(query, top_k=k)

        # Combinar y ordenar por similitud descendente
        combined = results_pub + results_priv
        combined.sort(key=lambda r: r.similitud, reverse=True)

        return combined[:k]

    def list_documents(self) -> list[dict]:
        """Lista documentos de ambas colecciones."""
        docs_pub = self.vs_public.list_documents()
        docs_priv = self.vs_private.list_documents()
        return docs_pub + docs_priv

    def delete_document(self, documento: str) -> int:
        """Elimina un documento de ambas colecciones."""
        count_pub = self.vs_public.delete_document(documento)
        count_priv = self.vs_private.delete_document(documento)
        return count_pub + count_priv

    def is_connected(self) -> bool:
        """Verifica la conexión con ChromaDB."""
        return self.vs_public.is_connected()


def get_vector_store_for_role(role: str):
    """
    Factory que retorna el VectorStore adecuado según el rol.
    
    - empleado: solo colección pública
    - gerente: ambas colecciones (MultiVectorStore)
    """
    if role == "gerente":
        return MultiVectorStore()
    return VectorStore()  # por defecto, colección pública
