# 🚀 Guía de Inicio Rápido (Día a Día)

Este documento contiene los comandos esenciales que necesitas para iniciar, usar y apagar el sistema RAG Empresarial en tu día a día, sin tener que volver a configurarlo todo.

---

## 1️⃣ Iniciar el Sistema

Para levantar todos los servicios, abre una terminal en esta misma carpeta (`RAG-Empresarial`) y ejecuta:

```bash
docker-compose up -d
```

> **Nota:** El parámetro `-d` hace que los contenedores corran en segundo plano, liberando tu terminal.
> *Asegúrate de que la aplicación de Docker Desktop esté abierta y funcionando antes de ejecutar este comando.*

## 2️⃣ Servicios y Enlaces Útiles

Una vez que el comando anterior finalice exitosamente, todos tus servicios estarán disponibles en los siguientes enlaces:

*   🌐 **Interfaz Web (Frontend):** [http://localhost](http://localhost) o [http://localhost:3000](http://localhost:3000)
    *   *Sube tus PDFs/DOCX y haz consultas.*
*   ⚙️ **Orquestador de Flujos (n8n):** [http://localhost:5678](http://localhost:5678)
    *   **Usuario:** `admin` / **Contraseña:** `admin123`
*   🔌 **Backend API (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
    *   *Documentación interactiva de tu API para pruebas directas.*

## 3️⃣ Ver el Estado de los Contenedores

Si alguna vez sientes que algo no carga o quieres asegurarte de que todo está vivo, ejecuta:

```bash
docker-compose ps
```
*(Deberían aparecer 4 contenedores con el estado `Up` o `running`)*

## 4️⃣ Apagar el Sistema

Cuando termines de trabajar y quieras apagar el sistema para liberar memoria RAM en tu computadora, ejecuta:

```bash
docker-compose down
```

> **Importante:** Este comando **no borra** tus documentos, ni tu historial, ni los flujos de n8n. Todo queda guardado de forma segura en tu disco para la próxima vez que inicies el proyecto.

## 🧹 (Opcional) Reiniciar desde Cero

Si alguna vez necesitas borrar **toda** la base de datos de documentos y configuraciones para empezar totalmente en blanco, usa:

```bash
docker-compose down -v
```
*(⚠️ Úsalo con cuidado, borrará todos los PDFs y la base de datos vectorial)*
