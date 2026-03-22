# Arquitectura del Sistema RAG Empresarial

## Diagrama de Flujo de Datos

### Pipeline de Ingesta (ETL)

```
Documento (PDF/DOCX)
        │
        ▼
┌─────────────────────┐
│  Document Processor  │  ← Extrae texto + metadata
│  (PyPDF / python-docx)│     (páginas, párrafos)
└──────────┬──────────┘
           │ texto plano
           ▼
┌─────────────────────┐
│      Chunker         │  ← Divide en fragmentos
│  (RecursiveCharText)  │     chunk_size=1000, overlap=200
└──────────┬──────────┘
           │ lista de chunks
           ▼
┌─────────────────────┐
│   Embeddings Service │  ← Vectoriza cada fragmento
│  (all-MiniLM-L6-v2)  │     dimensión: 384
└──────────┬──────────┘
           │ vectores + metadata
           ▼
┌─────────────────────┐
│      ChromaDB        │  ← Almacena vectores
│   (cosine similarity) │     con metadata de origen
└─────────────────────┘
```

### Pipeline de Consulta (RAG)

```
Pregunta del usuario
        │
        ▼
┌─────────────────────┐
│   Embeddings Service │  ← Vectoriza la pregunta
└──────────┬──────────┘
           │ query vector
           ▼
┌─────────────────────┐
│      ChromaDB        │  ← Búsqueda top-k
│  (cosine similarity)  │     por similitud de coseno
└──────────┬──────────┘
           │ k fragmentos más similares
           ▼
┌─────────────────────┐
│     RAG Engine       │  ← Construye contexto
│   (Context Builder)   │     a partir de fragmentos
└──────────┬──────────┘
           │ prompt con contexto
           ▼
┌─────────────────────┐
│     LLM (Ollama)     │  ← Genera respuesta
│   System Prompt RAG   │     citando fuentes
└──────────┬──────────┘
           │
           ▼
  Respuesta + Fuentes citadas
```

## Modelo de Datos

### Chunk (fragmento almacenado en ChromaDB)

| Campo | Tipo | Descripción |
|:--|:--|:--|
| `id` | string | `{documento}__chunk_{N}` |
| `document` | string | Texto del fragmento |
| `embedding` | float[384] | Vector del fragmento |
| `metadata.documento` | string | Nombre del archivo origen |
| `metadata.chunk_id` | int | Índice del fragmento |
| `metadata.pagina` | int | Página de origen (PDF) |
| `metadata.inicio` | int | Posición inicial en el texto |
| `metadata.fin` | int | Posición final en el texto |

## Decisiones de Diseño

### ¿Por qué `all-MiniLM-L6-v2`?
- Modelo ligero (~22M parámetros) que corre en CPU
- Embeddings de 384 dimensiones (eficiente)
- Soporte multilingüe aceptable para español
- Descarga de ~90MB (rápido en build Docker)

### ¿Por qué `RecursiveCharacterTextSplitter`?
- Respeta la estructura natural del texto (párrafos, oraciones)
- Separadores jerárquicos: `\n\n` → `\n` → `. ` → `, ` → ` `
- El overlap de 200 caracteres asegura que no se pierda contexto entre fragmentos

### ¿Por qué ChromaDB?
- Cero configuración (ideal para MVP)
- Soporta similitud de coseno nativa
- Persistencia en disco con Docker volumes
- API HTTP lista para producción
