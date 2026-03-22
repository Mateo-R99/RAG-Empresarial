# 🔍 RAG Empresarial — Sistema de Gestión Documental Inteligente

<div align="center">

![RAG](https://img.shields.io/badge/RAG-Retrieval_Augmented_Generation-6c63ff?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![n8n](https://img.shields.io/badge/n8n-Workflows-EA4B71?style=for-the-badge&logo=n8n&logoColor=white)

**Consulta tus documentos empresariales con lenguaje natural.**  
Respuestas precisas con trazabilidad de fuentes, orquestado con n8n.

</div>

---

## 📋 Tabla de Contenidos

- [Descripción](#-descripción)
- [Arquitectura](#-arquitectura)
- [Tecnologías](#-tecnologías)
- [Requisitos Previos](#-requisitos-previos)
- [Instalación Rápida](#-instalación-rápida)
- [Configuración](#-configuración)
- [Uso](#-uso)
- [API Endpoints](#-api-endpoints)
- [Flujos n8n](#-flujos-n8n)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Estrategias Anti-Alucinación](#-estrategias-anti-alucinación)
- [Personalización](#-personalización)
- [Troubleshooting](#-troubleshooting)

---

## 📖 Descripción

Sistema MVP que permite a usuarios hacer preguntas en **lenguaje natural** sobre documentos empresariales (PDF, DOCX) y recibir **respuestas precisas** con citas a las fuentes originales.

### ¿Cómo funciona?

```
📄 Documento → 🔪 Chunking → 🧮 Embeddings → 💾 ChromaDB
                                                    ↓
❓ Pregunta → 🧮 Embedding → 🔍 Búsqueda Top-K → 📋 Contexto → 🤖 LLM → 💬 Respuesta + Fuentes
```

1. **Ingesta**: Los documentos se dividen en fragmentos, se generan embeddings y se almacenan en ChromaDB
2. **Consulta**: La pregunta se convierte en embedding, se buscan los fragmentos más similares (top-k)
3. **Generación**: El LLM genera una respuesta basándose SOLO en los fragmentos recuperados, citando fuentes

---

## 🏗️ Arquitectura

```
┌──────────────────────────────────────────────────────────────────┐
│                        NGINX (Puerto 80)                        │
│                   Proxy Reverso + Frontend                      │
├──────────────┬───────────────────────────────────────────────────┤
│              │                                                   │
│   Frontend   │              Backend API (FastAPI)                │
│   Chat UI    │   ┌─────────┬──────────┬─────────┬──────────┐    │
│              │   │ /ingest │ /search  │ /query  │ /docs    │    │
│   HTML/CSS   │   └────┬────┴────┬─────┴────┬────┴──────────┘    │
│   JavaScript │        │         │          │                     │
│              │   ┌────▼────┐ ┌──▼───┐ ┌───▼────┐               │
│              │   │Processor│ │Vector│ │  RAG   │               │
│              │   │Chunker  │ │Store │ │ Engine │               │
│              │   │Embedder │ │      │ │        │               │
│              │   └────┬────┘ └──┬───┘ └───┬────┘               │
│              │        │         │          │                     │
├──────────────┤   ┌────▼─────────▼──┐  ┌───▼────────────┐       │
│              │   │    ChromaDB     │  │  Ollama (LLM)  │       │
│    n8n       │   │  Base Vectorial │  │  Local/Externo │       │
│  Workflows   │   │   Puerto 8100   │  │  Puerto 11434  │       │
│  Puerto 5678 │   └─────────────────┘  └────────────────┘       │
└──────────────┴──────────────────────────────────────────────────┘
```

### Componentes

| Componente | Descripción | Puerto |
|:--|:--|:--:|
| **Nginx** | Proxy reverso, sirve frontend | `80` |
| **FastAPI** | Backend API REST | `8000` |
| **ChromaDB** | Base de datos vectorial | `8100` |
| **n8n** | Orquestador de workflows | `5678` |
| **Ollama** | LLM local (externo) | `11434` |

---

## 🛠️ Tecnologías

| Capa | Tecnología | Propósito |
|:--|:--|:--|
| **Backend** | Python 3.11 + FastAPI | API REST async |
| **Embeddings** | `all-MiniLM-L6-v2` (sentence-transformers) | Vectorización de texto |
| **Vector DB** | ChromaDB | Almacenamiento y búsqueda vectorial |
| **LLM** | Ollama (llama3) / OpenAI | Generación de respuestas |
| **Chunking** | LangChain RecursiveCharacterTextSplitter | División inteligente de texto |
| **Orquestación** | n8n | Automatización de pipelines |
| **Frontend** | HTML/CSS/JS vanilla | Interfaz de chat |
| **Infraestructura** | Docker Compose | Contenedorización |
| **Proxy** | Nginx | Proxy reverso |

---

## 📦 Requisitos Previos

Antes de instalar, asegúrate de tener:

- [x] **Docker Desktop** instalado y ejecutándose ([descargar](https://www.docker.com/products/docker-desktop/))
- [x] **Ollama** instalado localmente ([descargar](https://ollama.ai/download))
- [x] **Git** para clonar el repositorio

### Instalar Ollama y descargar el modelo

```bash
# 1. Instalar Ollama (ya lo tienes si descargaste desde ollama.ai)

# 2. Descargar el modelo llama3
ollama pull llama3

# 3. Verificar que Ollama está corriendo
ollama list
```

> **💡 Tip:** Si prefieres un modelo más ligero, puedes usar `ollama pull llama3.2` o `ollama pull mistral`.

---

## 🚀 Instalación Rápida

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/RAG-Empresarial.git
cd RAG-Empresarial
```

### 2. Configurar variables de entorno

```bash
# Copiar archivo de ejemplo
cp .env.example .env

# Editar si necesitas cambiar algún valor (opcional)
# notepad .env   (Windows)
# nano .env      (Linux/Mac)
```

### 3. Asegurarse de que Ollama está corriendo

```bash
# Verificar que Ollama responde
curl http://localhost:11434/api/tags

# Si no está corriendo, iniciarlo:
ollama serve
```

### 4. Levantar todos los servicios

```bash
docker-compose up -d --build
```

> ⏱️ La primera vez tarda ~5-10 minutos porque descarga las imágenes de Docker y el modelo de embeddings.

### 5. Verificar que todo está funcionando

```bash
# Ver estado de los contenedores
docker-compose ps

# Health check del API
curl http://localhost/api/health
```

### 6. ¡Abrir la aplicación!

- 🌐 **Chat UI**: [http://localhost](http://localhost)
- 🔧 **n8n**: [http://localhost:5678](http://localhost:5678) (usuario: `admin`, contraseña: `admin123`)
- 📡 **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## ⚙️ Configuración

### Variables de entorno (.env)

| Variable | Valor por defecto | Descripción |
|:--|:--|:--|
| `LLM_PROVIDER` | `ollama` | Proveedor: `ollama` o `openai` |
| `OLLAMA_MODEL` | `llama3` | Modelo de Ollama a usar |
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | URL de Ollama |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Modelo de embeddings |
| `CHUNK_SIZE` | `1000` | Tamaño de cada fragmento (caracteres) |
| `CHUNK_OVERLAP` | `200` | Superposición entre fragmentos |
| `TOP_K` | `5` | Fragmentos recuperados por consulta |
| `TEMPERATURE` | `0.3` | Creatividad del LLM (0.0-2.0) |
| `N8N_USER` | `admin` | Usuario de n8n |
| `N8N_PASSWORD` | `admin123` | Contraseña de n8n |

### ¿Cuándo ajustar los parámetros?

| Situación | Ajuste recomendado |
|:--|:--|
| Respuestas muy genéricas | ↑ `TOP_K` a 8-10 |
| Respuestas con mezcla de temas | ↓ `TOP_K` a 3 |
| Fragmentos cortados a medio párrafo | ↑ `CHUNK_SIZE` a 1500 |
| Documentos muy largos | ↓ `CHUNK_SIZE` a 500 |
| Respuestas muy rígidas | ↑ `TEMPERATURE` a 0.5 |
| Alucinaciones frecuentes | ↓ `TEMPERATURE` a 0.1 |

---

## 💡 Uso

### Cargar un documento

**Opción A: Desde la interfaz web**
1. Abre [http://localhost](http://localhost)
2. Arrastra un PDF o DOCX a la zona de carga en la barra lateral
3. Espera a que se procese (verás el progreso)

**Opción B: Desde la API**
```bash
curl -X POST http://localhost/api/ingest \
  -F "archivo=@mi_documento.pdf"
```

**Opción C: Automáticamente con n8n**
1. Coloca documentos en la carpeta `data/documentos/`
2. El workflow de n8n los detectará y procesará automáticamente

### Hacer una consulta

**Desde la interfaz web:**
1. Escribe tu pregunta en el campo de texto
2. Presiona Enter o el botón de enviar
3. La respuesta aparecerá con las fuentes citadas (expandibles)

**Desde la API:**
```bash
curl -X POST http://localhost/api/query \
  -H "Content-Type: application/json" \
  -d '{"pregunta": "¿Cuáles son las políticas de vacaciones?"}'
```

**Respuesta ejemplo:**
```json
{
  "respuesta": "Según la política de la empresa, los empleados tienen derecho a 15 días hábiles de vacaciones anuales...",
  "fuentes": [
    {
      "documento": "politica_empresa.pdf",
      "fragmento": "Artículo 12. Vacaciones: Todo empleado con más de...",
      "chunk_id": 5,
      "similitud": 0.8732,
      "pagina": 3
    }
  ],
  "modelo_usado": "ollama/llama3",
  "fragmentos_consultados": 5
}
```

---

## 📡 API Endpoints

| Método | Ruta | Descripción |
|:--:|:--|:--|
| `GET` | `/api/health` | Estado de salud del sistema |
| `POST` | `/api/ingest` | Procesar e indexar un documento |
| `POST` | `/api/search` | Búsqueda semántica pura |
| `POST` | `/api/query` | Consulta RAG completa |
| `GET` | `/api/documents` | Listar documentos indexados |
| `DELETE` | `/api/documents/{nombre}` | Eliminar un documento |

> 📚 Documentación interactiva completa en: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🔄 Flujos n8n

### Flujo 1: Ingesta Automatizada

```
⏰ Trigger (cada 5 min) → 📁 Listar carpeta → 🔍 Filtrar PDF/DOCX → 📤 POST /api/ingest → 📝 Log
```

**Importar en n8n:**
1. Abre [http://localhost:5678](http://localhost:5678)
2. Ve a **Workflows** → **Import from File**
3. Selecciona `n8n/flujo_ingesta.json`

### Flujo 2: Consulta via Webhook

```
🌐 Webhook POST → ✅ Validar → 📤 POST /api/query → 📋 Formatear → 📨 Responder
```

**Uso después de importar y activar:**
```bash
curl -X POST http://localhost:5678/webhook/rag-query \
  -H "Content-Type: application/json" \
  -d '{"pregunta": "¿Cuál es la política de remoto?"}'
```

---

## 📁 Estructura del Proyecto

```
RAG-Empresarial/
├── 📄 docker-compose.yml         # Orquestación de servicios
├── 📄 .env.example               # Variables de entorno (plantilla)
├── 📄 .gitignore
├── 📄 README.md
│
├── 🐍 backend/                   # API FastAPI
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py               # Endpoints del API
│       ├── config.py             # Configuración central
│       ├── services/
│       │   ├── document_processor.py   # Extracción PDF/DOCX
│       │   ├── chunker.py              # División en fragmentos
│       │   ├── embeddings.py           # Generación de embeddings
│       │   ├── vector_store.py         # Operaciones ChromaDB
│       │   └── rag_engine.py           # Motor RAG con Ollama/OpenAI
│       ├── models/
│       │   └── schemas.py              # Modelos Pydantic
│       └── prompts/
│           └── system_prompt.py        # Prompt optimizado
│
├── 🌐 frontend/                  # Interfaz de chat
│   ├── index.html
│   ├── styles.css
│   └── app.js
│
├── 🔄 n8n/                       # Workflows exportados
│   ├── flujo_ingesta.json
│   └── flujo_consulta.json
│
├── 📂 data/
│   └── documentos/               # Documentos a procesar
│
├── 📂 nginx/
│   └── default.conf              # Configuración proxy
│
└── 📚 docs/
    ├── arquitectura.md
    └── despliegue.md
```

---

## 🛡️ Estrategias Anti-Alucinación

El sistema implementa múltiples estrategias para minimizar las alucinaciones del LLM:

| # | Estrategia | Implementación |
|:-:|:--|:--|
| 1 | **Prompt estricto** | El prompt instruye al LLM a responder SOLO con el contexto dado |
| 2 | **Temperatura baja** | Default 0.3 — menos creatividad, más precisión |
| 3 | **Citas obligatorias** | El prompt exige formato `[Fuente: documento, fragmento N]` |
| 4 | **Respuesta honesta** | Si no hay info suficiente, el LLM dice "No encontré información" |
| 5 | **Top-K ajustable** | Controla la cantidad de contexto vs. ruido |
| 6 | **Similitud visible** | El usuario ve el score de similitud de cada fuente |

---

## 🎨 Personalización

### Usar otro modelo de Ollama

```bash
# Descargar el modelo
ollama pull mistral

# Cambiar en .env
OLLAMA_MODEL=mistral
```

### Usar OpenAI en vez de Ollama

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-tu-api-key-aqui
OPENAI_MODEL=gpt-3.5-turbo
```

### Agregar soporte para más formatos

Edita `backend/app/services/document_processor.py` y añade un nuevo método `_process_xxx()`.

---

## 🔧 Troubleshooting

<details>
<summary><strong>❌ "No se pudo conectar con Ollama"</strong></summary>

1. Verifica que Ollama está corriendo: `ollama list`
2. Si no está corriendo: `ollama serve`
3. Verifica que el modelo está descargado: `ollama pull llama3`
4. URL correcta en `.env`: `OLLAMA_BASE_URL=http://host.docker.internal:11434`
</details>

<details>
<summary><strong>❌ Los contenedores no arrancan</strong></summary>

```bash
# Ver logs detallados
docker-compose logs -f

# Reconstruir todo
docker-compose down -v
docker-compose up -d --build
```
</details>

<details>
<summary><strong>❌ El API responde 502</strong></summary>

El API puede tardar ~30 segundos en cargar el modelo de embeddings. Espera un momento y reintenta.

```bash
# Verificar estado
docker-compose logs api
```
</details>

<details>
<summary><strong>❌ "No se pudo extraer texto del documento"</strong></summary>

- El PDF puede ser una imagen escaneada (sin texto seleccionable). Este MVP no incluye OCR.
- Verifica que el archivo no esté corrupto abriéndolo normalmente.
</details>

---

## 🚀 Comandos Útiles

```bash
# Iniciar todos los servicios
docker-compose up -d --build

# Ver logs en tiempo real
docker-compose logs -f

# Ver logs de un servicio específico
docker-compose logs -f api

# Detener todo
docker-compose down

# Detener y eliminar datos
docker-compose down -v

# Reconstruir solo el API
docker-compose up -d --build api

# Ver estado de los contenedores
docker-compose ps
```

---

## 📄 Licencia

MIT License

---

<div align="center">

**Hecho con 🧠 y ☕ — Sistema RAG Empresarial v1.0.0**

</div>
