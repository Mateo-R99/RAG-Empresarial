"""
API Principal del Sistema RAG Empresarial.
FastAPI con endpoints para ingesta, búsqueda semántica, consultas RAG,
autenticación JWT y control de acceso por roles.
"""

import os
import json
import shutil
import tempfile
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.models.schemas import (
    QueryRequest, QueryResponse,
    SearchRequest, SearchResponse, SearchResult as SearchResultSchema,
    IngestResponse, DocumentsResponse, DocumentInfo,
    HealthResponse,
    LoginRequest, LoginResponse, UserInfo,
    MetricsResponse, QueryHistoryItem,
)
from app.services.document_processor import DocumentProcessor
from app.services.chunker import Chunker
from app.services.embeddings import EmbeddingsService
from app.services.vector_store import VectorStore, get_vector_store_for_role
from app.services.rag_engine import RAGEngine
from app.services.auth import UserStore, create_access_token
from app.dependencies import get_current_user, RoleChecker

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
    logger.info(f"   Colección Pública: {settings.chroma_collection_public}")
    logger.info(f"   Colección Privada: {settings.chroma_collection_private}")
    logger.info(f"   JWT Expiración: {settings.jwt_expire_minutes} min")
    logger.info("=" * 60)

    # Pre-cargar el modelo de embeddings
    _ = EmbeddingsService()
    logger.info("✅ Modelo de embeddings cargado")

    # Asegurar que existe el archivo de usuarios
    UserStore()
    logger.info("✅ Almacén de usuarios inicializado")

    yield

    logger.info("Sistema RAG Empresarial detenido")


# ─── App ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="RAG Empresarial API",
    description="Sistema de Gestión Documental Inteligente basado en RAG con autenticación y roles",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════════
# ENDPOINTS DE AUTENTICACIÓN (Públicos)
# ═══════════════════════════════════════════════════════════════════════

@app.post("/api/auth/login", response_model=LoginResponse, tags=["Autenticación"])
async def login(request: LoginRequest):
    """
    Inicia sesión con usuario y contraseña.
    Retorna un token JWT para usar en endpoints protegidos.
    """
    user_store = UserStore()
    user = user_store.authenticate(request.username, request.password)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Credenciales incorrectas",
        )

    access_token = create_access_token(
        data={"sub": user["username"], "role": user["role"]}
    )

    return LoginResponse(
        access_token=access_token,
        role=user["role"],
        username=user["username"],
        nombre_completo=user["nombre_completo"],
    )


@app.get("/api/auth/me", response_model=UserInfo, tags=["Autenticación"])
async def get_me(current_user: dict = Depends(get_current_user)):
    """Retorna la información del usuario autenticado."""
    return UserInfo(
        username=current_user["username"],
        role=current_user["role"],
        nombre_completo=current_user["nombre_completo"],
    )


# ═══════════════════════════════════════════════════════════════════════
# ENDPOINTS PÚBLICOS
# ═══════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════
# ENDPOINTS PROTEGIDOS (Empleado + Gerente)
# ═══════════════════════════════════════════════════════════════════════

@app.post("/api/query", response_model=QueryResponse, tags=["Consulta RAG"])
async def rag_query(
    request: QueryRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Consulta RAG completa: busca fragmentos relevantes y genera
    una respuesta con el LLM, incluyendo fuentes citadas.
    
    - Empleados: busca solo en documentos públicos
    - Gerentes: busca en documentos públicos Y privados
    """
    try:
        engine = RAGEngine(role=current_user["role"])
        response = await engine.query(
            pregunta=request.pregunta,
            top_k=request.top_k,
            temperature=request.temperature,
            usuario=current_user["username"],
        )
        return response
    except Exception as e:
        logger.error(f"Error en consulta RAG: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error en consulta RAG: {str(e)}")


@app.post("/api/search", response_model=SearchResponse, tags=["Búsqueda"])
async def semantic_search(
    request: SearchRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Realiza una búsqueda semántica pura sobre los documentos indexados.
    Retorna los fragmentos más similares sin generar respuesta con LLM.
    
    - Empleados: busca solo en documentos públicos
    - Gerentes: busca en documentos públicos Y privados
    """
    try:
        vector_store = get_vector_store_for_role(current_user["role"])
        results = vector_store.search(request.consulta, top_k=request.top_k)

        return SearchResponse(
            resultados=[
                SearchResultSchema(
                    documento=r.documento,
                    fragmento=r.fragmento,
                    chunk_id=r.chunk_id,
                    similitud=r.similitud,
                    pagina=r.pagina,
                    coleccion=r.coleccion,
                )
                for r in results
            ],
            consulta_original=request.consulta,
            total_resultados=len(results),
        )
    except Exception as e:
        logger.error(f"Error en búsqueda: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error en búsqueda: {str(e)}")


@app.get("/api/documents", response_model=DocumentsResponse, tags=["Documentos"])
async def list_documents(current_user: dict = Depends(get_current_user)):
    """
    Lista todos los documentos indexados según el rol del usuario.
    
    - Empleados: ve solo documentos públicos
    - Gerentes: ve documentos públicos y privados
    """
    try:
        vector_store = get_vector_store_for_role(current_user["role"])
        docs = vector_store.list_documents()

        return DocumentsResponse(
            documentos=[
                DocumentInfo(
                    nombre=d["nombre"],
                    fragmentos=d["fragmentos"],
                    tipo=d["nombre"].rsplit(".", 1)[-1] if "." in d["nombre"] else "desconocido",
                    coleccion=d.get("coleccion"),
                )
                for d in docs
            ],
            total=len(docs),
        )
    except Exception as e:
        logger.error(f"Error listando documentos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error listando documentos: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════
# ENDPOINTS PROTEGIDOS (Solo Gerente)
# ═══════════════════════════════════════════════════════════════════════

@app.post("/api/ingest", response_model=IngestResponse, tags=["Ingesta"])
async def ingest_document(
    archivo: UploadFile = File(...),
    clasificacion: str = Form(default="publico"),
    current_user: dict = Depends(RoleChecker("gerente")),
):
    """
    Ingesta un documento: extrae texto, divide en fragmentos,
    genera embeddings y almacena en la base vectorial.
    
    Solo disponible para gerentes.
    
    - clasificacion: "publico" (visible para todos) o "privado" (solo gerentes)
    - Formatos soportados: PDF, DOCX
    """
    # Validar clasificación
    if clasificacion not in ("publico", "privado"):
        raise HTTPException(
            status_code=400,
            detail="Clasificación inválida. Use 'publico' o 'privado'."
        )

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

        # 3. Determinar colección según clasificación
        settings = get_settings()
        if clasificacion == "privado":
            collection_name = settings.chroma_collection_private
        else:
            collection_name = settings.chroma_collection_public

        # 4. Almacenar en base vectorial
        vector_store = VectorStore(collection_name=collection_name)
        fragmentos_creados = vector_store.add_documents(chunks)

        # 5. Guardar copia del documento
        dest_path = os.path.join(settings.documents_path, archivo.filename)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        shutil.copy2(tmp_path, dest_path)

        logger.info(
            f"✅ Documento '{archivo.filename}' procesado por {current_user['username']}: "
            f"{fragmentos_creados} fragmentos, {doc_result.caracteres} caracteres, "
            f"clasificación: {clasificacion}"
        )

        return IngestResponse(
            mensaje=f"Documento '{archivo.filename}' procesado exitosamente como {clasificacion}",
            documento=archivo.filename,
            fragmentos_creados=fragmentos_creados,
            caracteres_totales=doc_result.caracteres,
            clasificacion=clasificacion,
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


@app.delete("/api/documents/{nombre_documento}", tags=["Documentos"])
async def delete_document(
    nombre_documento: str,
    current_user: dict = Depends(RoleChecker("gerente")),
):
    """
    Elimina un documento y todos sus fragmentos de la base vectorial.
    Solo disponible para gerentes. Busca en ambas colecciones.
    """
    try:
        settings = get_settings()

        # Eliminar de ambas colecciones
        vs_pub = VectorStore(collection_name=settings.chroma_collection_public)
        vs_priv = VectorStore(collection_name=settings.chroma_collection_private)

        count_pub = vs_pub.delete_document(nombre_documento)
        count_priv = vs_priv.delete_document(nombre_documento)
        total_count = count_pub + count_priv

        if total_count == 0:
            raise HTTPException(status_code=404, detail=f"Documento '{nombre_documento}' no encontrado")

        # Eliminar archivo físico si existe
        file_path = os.path.join(settings.documents_path, nombre_documento)
        if os.path.exists(file_path):
            os.remove(file_path)

        logger.info(
            f"Documento '{nombre_documento}' eliminado por {current_user['username']} "
            f"({count_pub} fragmentos públicos, {count_priv} fragmentos privados)"
        )

        return {"mensaje": f"Documento '{nombre_documento}' eliminado ({total_count} fragmentos)"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando documento: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/api/metrics", response_model=MetricsResponse, tags=["Métricas"])
async def get_metrics(current_user: dict = Depends(RoleChecker("gerente"))):
    """
    Retorna métricas del sistema: documentos, fragmentos y consultas.
    Solo disponible para gerentes.
    """
    try:
        settings = get_settings()

        # Contar documentos y fragmentos por colección
        try:
            vs_pub = VectorStore(collection_name=settings.chroma_collection_public)
            docs_pub = vs_pub.list_documents()
            frags_pub = vs_pub.get_total_count()
        except Exception:
            docs_pub = []
            frags_pub = 0

        try:
            vs_priv = VectorStore(collection_name=settings.chroma_collection_private)
            docs_priv = vs_priv.list_documents()
            frags_priv = vs_priv.get_total_count()
        except Exception:
            docs_priv = []
            frags_priv = 0

        # Cargar historial de consultas
        history = []
        if os.path.exists(settings.query_history_path):
            try:
                with open(settings.query_history_path, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                history = []

        # Últimas 20 consultas
        recent = history[-20:] if history else []
        recent.reverse()  # Más recientes primero

        return MetricsResponse(
            total_documentos_publicos=len(docs_pub),
            total_documentos_privados=len(docs_priv),
            total_fragmentos_publicos=frags_pub,
            total_fragmentos_privados=frags_priv,
            total_consultas=len(history),
            consultas_recientes=[
                QueryHistoryItem(
                    usuario=q["usuario"],
                    pregunta=q["pregunta"],
                    timestamp=q["timestamp"],
                    fragmentos_usados=q["fragmentos_usados"],
                    rol=q.get("rol", "desconocido"),
                )
                for q in recent
            ],
        )
    except Exception as e:
        logger.error(f"Error obteniendo métricas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error obteniendo métricas: {str(e)}")


@app.get("/api/query-history", tags=["Métricas"])
async def get_query_history(
    limit: int = 50,
    current_user: dict = Depends(RoleChecker("gerente")),
):
    """
    Retorna el historial de consultas del sistema.
    Solo disponible para gerentes.
    """
    try:
        settings = get_settings()

        history = []
        if os.path.exists(settings.query_history_path):
            try:
                with open(settings.query_history_path, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                history = []

        # Retornar las últimas N, más recientes primero
        recent = history[-limit:] if history else []
        recent.reverse()

        return {
            "historial": recent,
            "total": len(history),
        }
    except Exception as e:
        logger.error(f"Error obteniendo historial: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
