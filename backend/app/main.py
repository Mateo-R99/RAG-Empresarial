"""
API Principal del Sistema RAG Empresarial.
FastAPI con endpoints para ingesta, búsqueda semántica y consultas RAG.
"""

import os
import shutil
import tempfile
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.models.schemas import (
    QueryRequest, QueryResponse,
    SearchRequest, SearchResponse, SearchResult as SearchResultSchema,
    IngestResponse, DocumentsResponse, DocumentInfo,
    HealthResponse,
)
from app.services.document_processor import DocumentProcessor
from app.services.chunker import Chunker
from app.services.embeddings import EmbeddingsService
from app.services.vector_store import VectorStore
from app.services.rag_engine import RAGEngine

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


# ─── Lifecycle ─────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicialización y limpieza de la aplicación."""
    settings = get_settings()
    logger.info("=" * 60)
    logger.info("🚀 Sistema RAG Empresarial iniciando...")
    logger.info(f"   LLM Provider: {settings.llm_provider}")
    logger.info(f"   Embedding Model: {settings.embedding_model}")
    logger.info(f"   Chunk Size: {settings.chunk_size} | Overlap: {settings.chunk_overlap}")
    logger.info(f"   Top-K: {settings.top_k} | Temperature: {settings.temperature}")
    logger.info("=" * 60)

    # Pre-cargar el modelo de embeddings
    _ = EmbeddingsService()
    logger.info("✅ Modelo de embeddings cargado")

    yield

    logger.info("Sistema RAG Empresarial detenido")


# ─── App ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="RAG Empresarial API",
    description="Sistema de Gestión Documental Inteligente basado en RAG",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Endpoints ─────────────────────────────────────────────────────────

@app.get("/api/health", response_model=HealthResponse, tags=["Sistema"])
async def health_check():
    """Verifica el estado de salud del sistema y sus componentes."""
    settings = get_settings()

    chroma_ok = False
    llm_ok = False

    try:
        vs = VectorStore()
        chroma_ok = vs.is_connected()
    except Exception:
        pass

    try:
        engine = RAGEngine()
        llm_ok = engine.is_llm_available()
    except Exception:
        pass

    return HealthResponse(
        estado="ok" if chroma_ok else "degradado",
        chroma_conectado=chroma_ok,
        llm_disponible=llm_ok,
        modelo_embeddings=settings.embedding_model,
        proveedor_llm=f"{settings.llm_provider}/{settings.ollama_model if settings.llm_provider == 'ollama' else settings.openai_model}",
    )


@app.post("/api/ingest", response_model=IngestResponse, tags=["Ingesta"])
async def ingest_document(archivo: UploadFile = File(...)):
    """
    Ingesta un documento: extrae texto, divide en fragmentos,
    genera embeddings y almacena en la base vectorial.
    
    Formatos soportados: PDF, DOCX
    """
    # Validar extensión
    if not archivo.filename:
        raise HTTPException(status_code=400, detail="El archivo debe tener un nombre")

    ext = os.path.splitext(archivo.filename)[1].lower()
    if ext not in {".pdf", ".docx"}:
        raise HTTPException(
            status_code=400,
            detail=f"Formato no soportado: {ext}. Use PDF o DOCX."
        )

    try:
        # Guardar temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            shutil.copyfileobj(archivo.file, tmp)
            tmp_path = tmp.name

        # 1. Extraer texto
        processor = DocumentProcessor()
        doc_result = processor.process(tmp_path, archivo.filename)

        if not doc_result.texto.strip():
            raise HTTPException(
                status_code=400,
                detail="No se pudo extraer texto del documento. Verifique que no esté vacío o sea una imagen."
            )

        # 2. Dividir en fragmentos
        chunker = Chunker()
        paginas_detalle = doc_result.metadata.get("paginas_detalle")
        chunks = chunker.split(
            doc_result.texto,
            doc_result.nombre,
            paginas_detalle=paginas_detalle
        )

        # 3. Almacenar en base vectorial (embeddings generados internamente)
        vector_store = VectorStore()
        fragmentos_creados = vector_store.add_documents(chunks)

        # 4. Guardar copia del documento
        settings = get_settings()
        dest_path = os.path.join(settings.documents_path, archivo.filename)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        shutil.copy2(tmp_path, dest_path)

        logger.info(
            f"✅ Documento '{archivo.filename}' procesado: "
            f"{fragmentos_creados} fragmentos, {doc_result.caracteres} caracteres"
        )

        return IngestResponse(
            mensaje=f"Documento '{archivo.filename}' procesado exitosamente",
            documento=archivo.filename,
            fragmentos_creados=fragmentos_creados,
            caracteres_totales=doc_result.caracteres,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error procesando documento: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error procesando documento: {str(e)}")
    finally:
        # Limpiar archivo temporal
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.post("/api/search", response_model=SearchResponse, tags=["Búsqueda"])
async def semantic_search(request: SearchRequest):
    """
    Realiza una búsqueda semántica pura sobre los documentos indexados.
    Retorna los fragmentos más similares sin generar respuesta con LLM.
    """
    try:
        vector_store = VectorStore()
        results = vector_store.search(request.consulta, top_k=request.top_k)

        return SearchResponse(
            resultados=[
                SearchResultSchema(
                    documento=r.documento,
                    fragmento=r.fragmento,
                    chunk_id=r.chunk_id,
                    similitud=r.similitud,
                    pagina=r.pagina,
                )
                for r in results
            ],
            consulta_original=request.consulta,
            total_resultados=len(results),
        )
    except Exception as e:
        logger.error(f"Error en búsqueda: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error en búsqueda: {str(e)}")


@app.post("/api/query", response_model=QueryResponse, tags=["Consulta RAG"])
async def rag_query(request: QueryRequest):
    """
    Consulta RAG completa: busca fragmentos relevantes y genera
    una respuesta con el LLM, incluyendo fuentes citadas.
    """
    try:
        engine = RAGEngine()
        response = await engine.query(
            pregunta=request.pregunta,
            top_k=request.top_k,
            temperature=request.temperature,
        )
        return response
    except Exception as e:
        logger.error(f"Error en consulta RAG: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error en consulta RAG: {str(e)}")


@app.get("/api/documents", response_model=DocumentsResponse, tags=["Documentos"])
async def list_documents():
    """Lista todos los documentos indexados en la base vectorial."""
    try:
        vector_store = VectorStore()
        docs = vector_store.list_documents()

        return DocumentsResponse(
            documentos=[
                DocumentInfo(
                    nombre=d["nombre"],
                    fragmentos=d["fragmentos"],
                    tipo=d["nombre"].rsplit(".", 1)[-1] if "." in d["nombre"] else "desconocido",
                )
                for d in docs
            ],
            total=len(docs),
        )
    except Exception as e:
        logger.error(f"Error listando documentos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error listando documentos: {str(e)}")


@app.delete("/api/documents/{nombre_documento}", tags=["Documentos"])
async def delete_document(nombre_documento: str):
    """Elimina un documento y todos sus fragmentos de la base vectorial."""
    try:
        vector_store = VectorStore()
        count = vector_store.delete_document(nombre_documento)

        if count == 0:
            raise HTTPException(status_code=404, detail=f"Documento '{nombre_documento}' no encontrado")

        # Eliminar archivo físico si existe
        settings = get_settings()
        file_path = os.path.join(settings.documents_path, nombre_documento)
        if os.path.exists(file_path):
            os.remove(file_path)

        return {"mensaje": f"Documento '{nombre_documento}' eliminado ({count} fragmentos)"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando documento: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
