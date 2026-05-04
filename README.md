# 🔍 RAG Empresarial — Sistema de Gestión Documental Inteligente (v2)

<div align="center">

![RAG](https://img.shields.io/badge/RAG-Retrieval_Augmented_Generation-6c63ff?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Auth](https://img.shields.io/badge/Auth-JWT_Roles-F59E0B?style=for-the-badge&logo=jsonwebtokens&logoColor=white)

**Consulta tus documentos empresariales con lenguaje natural y control de acceso.**  
Respuestas precisas con trazabilidad de fuentes, protegido mediante JWT y roles de usuario.

</div>

---

## 📋 Tabla de Contenidos

- [Descripción](#-descripción)
- [Sistema de Roles y Autenticación](#-sistema-de-roles-y-autenticación)
- [Arquitectura](#-arquitectura)
- [Tecnologías](#-tecnologías)
- [Requisitos Previos](#-requisitos-previos)
- [Instalación Rápida](#-instalación-rápida)
- [Configuración](#-configuración)
- [Uso](#-uso)
- [API Endpoints](#-api-endpoints)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Troubleshooting](#-troubleshooting)

---

## 📖 Descripción

Sistema MVP que permite a usuarios hacer preguntas en **lenguaje natural** sobre documentos empresariales (PDF, DOCX) y recibir **respuestas precisas** con citas a las fuentes originales. 

### ¿Cómo funciona?

```
📄 Documento → 🔪 Chunking → 🧮 Embeddings → 💾 ChromaDB (Público/Privado)
                                                     ↓
👤 Login JWT → ❓ Pregunta → 🔍 Búsqueda Top-K (según rol) → 🤖 LLM → 💬 Respuesta
```

---

## 🔐 Sistema de Roles y Autenticación

El sistema cuenta con Autenticación JWT y control de accesos basado en roles (RBAC).

| Rol | Privilegios y Accesos |
|:--|:--|
| **Empleado** | - Solo puede consultar documentos de la colección **Pública**.<br>- No puede subir ni eliminar documentos.<br>- No tiene acceso a métricas del sistema. |
| **Gerente** | - Puede consultar documentos de la colección **Pública** y **Privada**.<br>- Puede subir documentos y elegir su clasificación (Público/Privado).<br>- Puede eliminar documentos.<br>- Tiene acceso a métricas y estadísticas del sistema. |

*Los usuarios por defecto se encuentran configurados en `backend/users.json`.*

---

## 🏗️ Arquitectura

```
┌──────────────────────────────────────────────────────────────────┐
│                        NGINX (Puerto 80)                         │
│                   Proxy Reverso + Frontend UI                    │
├──────────────┬───────────────────────────────────────────────────┤
│              │                                                   │
│   Frontend   │              Backend API (FastAPI)                │
│  (Login UI)  │   ┌────────┬─────────┬─────────┬────────┬───────┐ │
│              │   │ /auth  │ /ingest │ /search │ /query │ /docs │ │
│   HTML/CSS   │   └────┬───┴────┬────┴────┬────┴────┬───┴───────┘ │
│   JavaScript │        │        │         │         │             │
│              │   ┌────▼────────▼──┐ ┌────▼─────────▼──┐          │
│              │   │ Auth & Roles   │ │   RAG Engine    │          │
│              │   │ JWT Validation │ │ Vector & Models │          │
│              │   └────┬───────────┘ └────┬─────────┬──┘          │
├──────────────┤        │                  │         │             │
│              │   ┌────▼───────┐ ┌────────▼─────┐ ┌─▼───────────┐ │
│    n8n       │   │ users.json │ │   ChromaDB   │ │   Ollama    │ │
│  Workflows   │   │  (Mock DB) │ │ (Pub / Priv) │ │ Local / Ext │ │
│  Puerto 5678 │   └────────────┘ └──────────────┘ └─────────────┘ │
└──────────────┴───────────────────────────────────────────────────┘
```

---

## 🛠️ Tecnologías

| Capa | Tecnología | Propósito |
|:--|:--|:--|
| **Backend** | Python 3.11 + FastAPI | API REST async |
| **Seguridad** | PyJWT, bcrypt | Autenticación y hash de contraseñas |
| **Embeddings** | `all-MiniLM-L6-v2` | Vectorización de texto |
| **Vector DB** | ChromaDB | Colecciones públicas y privadas |
| **LLM** | Ollama (llama3) / OpenAI | Generación de respuestas |
| **Frontend** | HTML/CSS/JS (Vanilla) | Interfaz responsiva con Glassmorphism |
| **Orquestación**| n8n | Automatización de procesos |
| **Infraestructura**| Docker Compose | Contenedorización completa |

---

## 📦 Requisitos Previos

- [x] **Docker Desktop** instalado y ejecutándose ([descargar](https://www.docker.com/products/docker-desktop/))
- [x] **Ollama** instalado localmente ([descargar](https://ollama.ai/download))
- [x] **Git** para clonar el repositorio

### Instalar Ollama y descargar el modelo

```bash
# Descargar el modelo llama3
ollama pull llama3

# Verificar que Ollama está corriendo
ollama list
```

---

## 🚀 Instalación Rápida

1. **Clonar y configurar**
```bash
git clone https://github.com/tu-usuario/RAG-Empresarial.git
cd RAG-Empresarial
cp .env.example .env
```

2. **Levantar servicios**
```bash
docker-compose up -d --build
```
> ⏱️ La primera vez tarda ~5-10 minutos porque descarga las imágenes y dependencias.

3. **¡Abrir la aplicación!**
- 🌐 **Chat UI**: [http://localhost](http://localhost)
- 🔌 **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- ⚙️ **n8n**: [http://localhost:5678](http://localhost:5678)

---

## ⚙️ Configuración (.env)

Las nuevas variables más importantes para la versión 2.0 son:

| Variable | Valor por defecto | Descripción |
|:--|:--|:--|
| `LLM_PROVIDER` | `ollama` | Proveedor: `ollama` o `openai` |
| `OLLAMA_MODEL` | `llama3` | Modelo de Ollama a usar |
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | URL de Ollama |
| `JWT_SECRET_KEY` | `rag-empresarial-secret-key...` | Clave para firmar los tokens JWT |
| `JWT_EXPIRE_MINUTES` | `480` | Tiempo de expiración del token (8 horas) |

---

## 💡 Uso

### Autenticación
Para utilizar el sistema desde el frontend en `http://localhost`, debes iniciar sesión con uno de los usuarios configurados en `backend/users.json`. 

- **Ejemplo Gerente**: `m.gomez` / `Gerente2024*`
- **Ejemplo Empleado**: `a.lopez` / `Empleado2024*`

### Cargar un documento (Solo Gerentes)
1. Inicia sesión como gerente.
2. Usa el panel lateral izquierdo para elegir la **Clasificación** (Público o Privado).
3. Arrastra tu documento a la zona de carga.

### Consultar Documentos
1. Escribe tu pregunta en el chat.
2. El sistema buscará únicamente en las colecciones a las que tu rol te dé acceso.
3. El LLM responderá citando las fuentes extraídas de los documentos originales.

---

## 📡 API Endpoints

| Método | Ruta | Rol Requerido | Descripción |
|:--:|:--|:--|:--|
| `POST` | `/api/auth/login` | Público | Autenticación y obtención de JWT |
| `GET` | `/api/auth/me` | Autenticado | Información del usuario actual |
| `GET` | `/api/health` | Público | Estado de salud del sistema |
| `POST` | `/api/query` | Autenticado | Consulta RAG (Contexto según rol) |
| `GET` | `/api/documents` | Autenticado | Listar documentos (Públicos o Privados según rol) |
| `POST` | `/api/ingest` | Gerente | Procesar e indexar un documento PDF/DOCX |
| `DELETE` | `/api/documents/{nombre}` | Gerente | Eliminar un documento |
| `GET` | `/api/metrics` | Gerente | Estadísticas de uso y base vectorial |

---

## 🔧 Troubleshooting

<details>
<summary><strong>❌ Error 500 al generar respuesta (Ollama)</strong></summary>

Si Ollama arroja un Internal Server Error, generalmente se debe a que la consulta + contexto exceden el `num_ctx` configurado. Esto ya fue mitigado en v2, pero asegúrate de que Ollama esté ejecutándose correctamente y tu máquina tenga RAM suficiente.
</details>

<details>
<summary><strong>❌ "No se pudo conectar con Ollama"</strong></summary>

1. Verifica que Ollama está corriendo: `ollama list`
2. Si no está corriendo: `ollama serve`
3. Asegúrate de que `OLLAMA_BASE_URL` en el `.env` apunte a `http://host.docker.internal:11434` en Docker Windows/Mac.
</details>

---

## 📄 Licencia

MIT License

---

<div align="center">

**Hecho con 🧠 y ☕ — Sistema RAG Empresarial v2.0.0**

</div>
