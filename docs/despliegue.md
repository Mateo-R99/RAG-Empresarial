# Guía de Despliegue — RAG Empresarial

## Requisitos Mínimos del Sistema

| Recurso | Mínimo | Recomendado |
|:--|:--|:--|
| **RAM** | 8 GB | 16 GB |
| **CPU** | 4 cores | 8 cores |
| **Disco** | 10 GB libres | 20 GB libres |
| **Docker** | 20.10+ | Última versión |
| **Docker Compose** | v2.0+ | Última versión |

## Paso 1: Instalar requisitos

### Docker Desktop (Windows/Mac)
1. Descarga desde [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/)
2. Instala y reinicia el sistema
3. Verifica: `docker --version` y `docker compose version`

### Ollama
1. Descarga desde [ollama.ai/download](https://ollama.ai/download)
2. Instala el programa
3. Descarga el modelo:
```bash
ollama pull llama3
```
4. Verifica que está corriendo:
```bash
curl http://localhost:11434/api/tags
```

## Paso 2: Configurar el proyecto

```bash
# Clonar
git clone https://github.com/tu-usuario/RAG-Empresarial.git
cd RAG-Empresarial

# Configurar
cp .env.example .env
```

Edita `.env` solo si necesitas cambiar valores (los defaults funcionan para MVP).

## Paso 3: Levantar servicios

```bash
# Construir y arrancar (primera vez ~5-10 min)
docker-compose up -d --build

# Verificar estado
docker-compose ps
```

Deberías ver 4 contenedores `running`:
```
NAME          STATUS     PORTS
rag-api       running    0.0.0.0:8000->8000
rag-chroma    running    0.0.0.0:8100->8000
rag-n8n       running    0.0.0.0:5678->5678
rag-nginx     running    0.0.0.0:80->80
```

## Paso 4: Verificar

```bash
# Health check
curl http://localhost/api/health

# Resultado esperado:
# {"estado":"ok","chroma_conectado":true,"llm_disponible":true,...}
```

## Paso 5: Importar flujos n8n

1. Abre [http://localhost:5678](http://localhost:5678)
2. Login: `admin` / `admin123`
3. **Workflows** → **Import from File**
4. Importa `n8n/flujo_ingesta.json`
5. Importa `n8n/flujo_consulta.json`
6. Activa ambos workflows

## Paso 6: Usar el sistema

1. Abre [http://localhost](http://localhost)
2. Sube un documento PDF o DOCX desde la barra lateral
3. Haz una pregunta sobre el documento
4. ¡Listo! La respuesta incluirá citas de las fuentes

## Detener el sistema

```bash
# Detener (preserva datos)
docker-compose down

# Detener y eliminar todos los datos
docker-compose down -v
```

## Actualizar

```bash
git pull
docker-compose up -d --build
```
