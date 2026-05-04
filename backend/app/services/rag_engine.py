"""
Motor RAG: orquesta búsqueda semántica + generación de respuestas con LLM.
Soporta Ollama (local) y OpenAI como proveedores de LLM.
Con soporte de roles para búsqueda en colecciones adecuadas.
"""

import json
import os
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from openai import OpenAI

from app.config import get_settings
from app.services.vector_store import VectorStore, MultiVectorStore, SearchResult, get_vector_store_for_role
from app.prompts.system_prompt import SYSTEM_PROMPT
from app.models.schemas import QueryResponse, FuenteInfo

logger = logging.getLogger(__name__)


class RAGEngine:
    """Motor de Retrieval-Augmented Generation con soporte de roles."""

    def __init__(self, role: str = "empleado"):
        self.vector_store = get_vector_store_for_role(role)
        self.settings = get_settings()
        self.role = role

    async def query(
        self,
        pregunta: str,
        top_k: Optional[int] = None,
        temperature: Optional[float] = None,
        usuario: str = "anónimo",
    ) -> QueryResponse:
        """
        Ejecuta el pipeline RAG completo:
        1. Busca fragmentos relevantes en la base vectorial (según rol)
        2. Construye contexto con los fragmentos
        3. Genera respuesta con el LLM
        4. Formatea respuesta con fuentes
        5. Registra la consulta en el historial

        Args:
            pregunta: Pregunta del usuario en lenguaje natural
            top_k: Número de fragmentos a recuperar
            temperature: Temperatura del LLM
            usuario: Nombre del usuario que realiza la consulta

        Returns:
            QueryResponse con respuesta y fuentes citadas
        """
        k = top_k or self.settings.top_k
        temp = temperature or self.settings.temperature

        # 1. Búsqueda semántica
        logger.info(f"RAG Query [{self.role}]: '{pregunta}' (top_k={k}, temp={temp})")
        resultados = self.vector_store.search(pregunta, top_k=k)

        if not resultados:
            # Registrar consulta sin resultados
            self._record_query(usuario, pregunta, 0)
            return QueryResponse(
                respuesta="No encontré documentos relevantes para responder tu pregunta. Asegúrate de haber cargado documentos al sistema.",
                fuentes=[],
                pregunta_original=pregunta,
                modelo_usado=self._get_model_name(),
                fragmentos_consultados=0,
            )

        # 2. Construir contexto
        contexto = self._build_context(resultados)

        # 3. Generar respuesta con LLM
        prompt = SYSTEM_PROMPT.format(contexto=contexto, pregunta=pregunta)
        respuesta = await self._call_llm(prompt, temp)

        # 4. Construir fuentes
        fuentes = [
            FuenteInfo(
                documento=r.documento,
                fragmento=r.fragmento[:300] + "..." if len(r.fragmento) > 300 else r.fragmento,
                chunk_id=r.chunk_id,
                similitud=r.similitud,
                pagina=r.pagina,
                coleccion=r.coleccion,
            )
            for r in resultados
        ]

        # 5. Registrar consulta en historial
        self._record_query(usuario, pregunta, len(resultados))

        return QueryResponse(
            respuesta=respuesta,
            fuentes=fuentes,
            pregunta_original=pregunta,
            modelo_usado=self._get_model_name(),
            fragmentos_consultados=len(resultados),
        )

    def _build_context(self, resultados: list[SearchResult]) -> str:
        """Construye el contexto textual a partir de los resultados de búsqueda."""
        context_parts = []

        for i, r in enumerate(resultados, 1):
            header = f"--- Fragmento {i} | Documento: {r.documento}"
            if r.pagina:
                header += f" | Página: {r.pagina}"
            header += f" | Similitud: {r.similitud:.2%} ---"

            context_parts.append(f"{header}\n{r.fragmento}")

        return "\n\n".join(context_parts)

    async def _call_llm(self, prompt: str, temperature: float) -> str:
        """Llama al LLM configurado (Ollama o OpenAI)."""
        if self.settings.llm_provider == "ollama":
            return await self._call_ollama(prompt, temperature)
        elif self.settings.llm_provider == "openai":
            return self._call_openai(prompt, temperature)
        else:
            raise ValueError(f"Proveedor LLM no soportado: {self.settings.llm_provider}")

    async def _call_ollama(self, prompt: str, temperature: float) -> str:
        """Genera respuesta usando Ollama (local)."""
        url = f"{self.settings.ollama_base_url}/api/generate"

        payload = {
            "model": self.settings.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": 2048,
                "num_ctx": 8192,
            }
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("response", "Error: respuesta vacía de Ollama")
        except httpx.ConnectError:
            logger.error(f"No se puede conectar a Ollama en {self.settings.ollama_base_url}")
            return (
                "⚠️ No se pudo conectar con Ollama. "
                "Asegúrate de que Ollama esté ejecutándose localmente con: `ollama serve` "
                f"y que el modelo '{self.settings.ollama_model}' esté descargado con: "
                f"`ollama pull {self.settings.ollama_model}`"
            )
        except Exception as e:
            logger.error(f"Error llamando a Ollama: {e}")
            return f"Error al generar respuesta con Ollama: {str(e)}"

    def _call_openai(self, prompt: str, temperature: float) -> str:
        """Genera respuesta usando OpenAI API."""
        if not self.settings.openai_api_key:
            return "⚠️ No se configuró OPENAI_API_KEY. Configúrala en el archivo .env"

        client = OpenAI(api_key=self.settings.openai_api_key)

        try:
            response = client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=2048,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error llamando a OpenAI: {e}")
            return f"Error al generar respuesta con OpenAI: {str(e)}"

    def _get_model_name(self) -> str:
        """Retorna el nombre del modelo LLM en uso."""
        if self.settings.llm_provider == "ollama":
            return f"ollama/{self.settings.ollama_model}"
        return f"openai/{self.settings.openai_model}"

    def is_llm_available(self) -> bool:
        """Verifica si el LLM configurado está disponible."""
        try:
            if self.settings.llm_provider == "ollama":
                response = httpx.get(
                    f"{self.settings.ollama_base_url}/api/tags",
                    timeout=5.0
                )
                return response.status_code == 200
            elif self.settings.llm_provider == "openai":
                return bool(self.settings.openai_api_key)
        except Exception:
            return False
        return False

    def _record_query(self, usuario: str, pregunta: str, fragmentos: int):
        """Registra una consulta en el archivo de historial JSON."""
        try:
            history_path = self.settings.query_history_path
            os.makedirs(os.path.dirname(history_path), exist_ok=True)

            # Cargar historial existente
            history = []
            if os.path.exists(history_path):
                try:
                    with open(history_path, "r", encoding="utf-8") as f:
                        history = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError):
                    history = []

            # Agregar nueva entrada
            entry = {
                "usuario": usuario,
                "pregunta": pregunta,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "fragmentos_usados": fragmentos,
                "rol": self.role,
            }
            history.append(entry)

            # Mantener solo las últimas 500 consultas
            if len(history) > 500:
                history = history[-500:]

            # Guardar
            with open(history_path, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.warning(f"No se pudo registrar consulta en historial: {e}")
