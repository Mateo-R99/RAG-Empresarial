"""
Modelos Pydantic para request/response del API.
"""

from pydantic import BaseModel, Field
from typing import Optional


# ─── Auth ──────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    """Solicitud de inicio de sesión."""
    username: str = Field(..., description="Nombre de usuario", min_length=1)
    password: str = Field(..., description="Contraseña", min_length=1)


class LoginResponse(BaseModel):
    """Respuesta exitosa de inicio de sesión."""
    access_token: str = Field(..., description="Token JWT de acceso")
    token_type: str = Field(default="bearer", description="Tipo de token")
    role: str = Field(..., description="Rol del usuario (empleado/gerente)")
    username: str = Field(..., description="Nombre de usuario")
    nombre_completo: str = Field(..., description="Nombre completo del usuario")


class UserInfo(BaseModel):
    """Información del usuario autenticado."""
    username: str
    role: str
    nombre_completo: str


# ─── Requests ──────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    """Solicitud de consulta RAG."""
    pregunta: str = Field(..., description="Pregunta en lenguaje natural", min_length=3)
    top_k: Optional[int] = Field(None, description="Número de fragmentos a recuperar", ge=1, le=20)
    temperature: Optional[float] = Field(None, description="Temperatura del LLM", ge=0.0, le=2.0)


class SearchRequest(BaseModel):
    """Solicitud de búsqueda semántica."""
    consulta: str = Field(..., description="Texto de búsqueda", min_length=3)
    top_k: Optional[int] = Field(None, description="Número de resultados", ge=1, le=20)


# ─── Responses ─────────────────────────────────────────────────────────

class FuenteInfo(BaseModel):
    """Información de una fuente citada."""
    documento: str = Field(..., description="Nombre del documento fuente")
    fragmento: str = Field(..., description="Texto del fragmento relevante")
    chunk_id: int = Field(..., description="Número del fragmento")
    similitud: float = Field(..., description="Score de similitud (0-1)")
    pagina: Optional[int] = Field(None, description="Página del documento (si aplica)")
    coleccion: Optional[str] = Field(None, description="Colección de origen (publico/privado)")


class QueryResponse(BaseModel):
    """Respuesta a una consulta RAG."""
    respuesta: str = Field(..., description="Respuesta generada por el LLM")
    fuentes: list[FuenteInfo] = Field(default_factory=list, description="Fuentes utilizadas")
    pregunta_original: str = Field(..., description="Pregunta original del usuario")
    modelo_usado: str = Field(..., description="Modelo LLM utilizado")
    fragmentos_consultados: int = Field(..., description="Número de fragmentos recuperados")


class SearchResult(BaseModel):
    """Resultado de búsqueda semántica."""
    documento: str
    fragmento: str
    chunk_id: int
    similitud: float
    pagina: Optional[int] = None
    coleccion: Optional[str] = None


class SearchResponse(BaseModel):
    """Respuesta de búsqueda semántica."""
    resultados: list[SearchResult]
    consulta_original: str
    total_resultados: int


class IngestResponse(BaseModel):
    """Respuesta de ingesta de documento."""
    mensaje: str
    documento: str
    fragmentos_creados: int
    caracteres_totales: int
    clasificacion: str = Field(..., description="Clasificación del documento: publico o privado")


class DocumentInfo(BaseModel):
    """Información de un documento indexado."""
    nombre: str
    fragmentos: int
    tipo: str
    coleccion: Optional[str] = None


class DocumentsResponse(BaseModel):
    """Lista de documentos indexados."""
    documentos: list[DocumentInfo]
    total: int


class HealthResponse(BaseModel):
    """Estado de salud del sistema."""
    estado: str = "ok"
    version: str = "1.0.0"
    chroma_conectado: bool = False
    llm_disponible: bool = False
    modelo_embeddings: str = ""
    proveedor_llm: str = ""


# ─── Métricas y Historial (Solo Gerente) ──────────────────────────────

class QueryHistoryItem(BaseModel):
    """Elemento del historial de consultas."""
    usuario: str
    pregunta: str
    timestamp: str
    fragmentos_usados: int
    rol: str


class MetricsResponse(BaseModel):
    """Estadísticas del sistema."""
    total_documentos_publicos: int
    total_documentos_privados: int
    total_fragmentos_publicos: int
    total_fragmentos_privados: int
    total_consultas: int
    consultas_recientes: list[QueryHistoryItem]
