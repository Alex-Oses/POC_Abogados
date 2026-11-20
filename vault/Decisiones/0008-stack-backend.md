# 0008 — Stack del backend

- **Estado**: Aceptada (2026-11-20, @Rubén)
- **Fecha**: 2026-11-16
- **Autor**: @ia-opencode-ruben
- **Se decide con**: @Rubén (backend), @Marina (BD), @Kevin (despliegue), @Alex (OCR), @Yaser (ETL)
- **Votos**: @Rubén (backend), 2026-11-17: **Python + FastAPI**. @Rubén, 2026-11-20: **cerrada** con el visto bueno del resto del equipo; @Marina, @Kevin, @Alex y @Yaser no revisan la bóveda, así que su conformidad se recogió fuera del repo.

## Contexto

El contrato v1 ([docs/api/endpoints.md](../../docs/api/endpoints.md)) son 40 rutas REST y JSON sobre PostgreSQL 14+ con Flyway. Alrededor hay cuatro piezas ya decididas que condicionan el lenguaje:

| Pieza | Decidida en | En qué está escrito |
|---|---|---|
| OCR | [[0001-ocr-local-paddleocr-vl]] | Python (PaddleOCR-VL), servido por Ollama vía HTTP |
| Anonimización | [[0006-presidio-anonimizacion-local]] | Python (Presidio + spaCy) |
| PDF final | [[0007-generacion-pdf-final]] | Python (`reportlab`) |
| Migraciones | [[0002-postgresql]] | SQL plano con Flyway |

Hoy el lenguaje del backend **no está escrito en ningún sitio**: solo se deduce de las dependencias de [[0007-generacion-pdf-final]]. Esta nota lo pone en Propuesta.

Restricciones que no se negocian:

- 100 % local, en el servidor del Colegio (Windows Server o Linux) con GPU NVIDIA.
- Una sola persona en backend: cada runtime extra es coste de mantenimiento.
- Licencias permisivas en todo lo que se distribuya o inspeccione (AGPL descartada en 0007).
- El contrato y el modelo no dependen del lenguaje: JSON, `snake_case` idéntico a las columnas, SQL explícito.

## Decisión

**Python 3.12 + FastAPI + Uvicorn**, `psycopg` 3 con SQL explícito y Pydantic v2 para los esquemas. Flyway sigue siendo el único que migra: la aplicación no crea ni altera tablas.

| Criterio | Python + FastAPI | C# + ASP.NET Core |
|---|---|---|
| Presidio (anonimización) | Nativo | Sidecar Python obligatorio |
| PaddleOCR-VL y cliente de Ollama | Nativo | HTTP o sidecar |
| PDF con `reportlab` | Nativo, MIT/BSD | QuestPDF (revisar licencia) o MigraDoc (MIT) |
| Driver PostgreSQL | `psycopg` 3 (LGPL, uso dinámico) | Npgsql, maduro |
| Contratos y validación | Pydantic v2, un esquema por payload | Minimal APIs + records, `System.Text.Json` |
| Rendimiento | Suficiente: casi todo es espera de E/S (OCR, BD, PDF) | Algo mejor en CPU pura, irrelevante aquí |
| Despliegue local | Una `venv` + `uvicorn`; o contenedor | `dotnet publish` autocontenido, o contenedor |
| Depuración en el servidor del Colegio | Un runtime, sin CLR ni IIS | Si el ICAT ya tiene IIS/Active Directory, encaja mejor |
| Mercado laboral en Tarragona | Amplio | Más caro y menos gente disponible |
| Coste de licencias | 0 | 0 si se elige bien el motor de PDF |

**Por qué Python gana hoy:** las tres piezas caras del proyecto (OCR, anonimización y PDF) ya son Python. Una API en C# obliga a un segundo runtime, un segundo CI y un contrato interno HTTP entre ambos, para no ahorrar nada medible: el cuello de botella es la GPU del OCR, no el servidor HTTP.

## Alternativa: C# + ASP.NET Core

Es una opción legítima, no un descarte. Minimal APIs + Npgsql cubren el contrato entero y el tipado es mejor que Python. Elegirla si se cumple alguna de estas:

- El ICAT o el equipo de soporte mantiene el sistema y solo sabe .NET, con IIS y Active Directory ya montados.
- Requisito de despliegue como servicio de Windows firmado.
- Presidio y PaddleOCR se consumen ya como servicios aparte (sidecar) por otro motivo.

Coste de elegirla: **un servicio Python adicional** para Presidio y el render del PDF (PaddleOCR ya vive en Ollama), y dos pipelines de pruebas. Nada insalvable, pero es trabajo que no da funcionalidad nueva.

## Lo que NO cambia con la decisión

- El contrato HTTP, los estados y las reglas. Es agnóstico del lenguaje.
- El modelo de datos y Flyway.
- El diseño del PDF: `reportlab` solo es la implementación de la opción 1 de [[0007-generacion-pdf-final]]; otro motor de PDF tendría que reproducir el mismo JSON de estructura y el mismo hash.

Por eso la decisión es barata de revertir **hoy** y cara después de escribir el primer endpoint con su capa de validación.

## Consecuencias

- **Una sola imagen/runtime** para API, OCR-worker, anonimización y PDF: un `requirements` o un `pyproject.toml`, un job de CI.
- **Tipado:** Pydantic v2 como contrato en tiempo de ejecución; `mypy` en modo laxo al principio. Sin esto, el contrato de 40 rutas se desincroniza del código.
- **Tareas largas:** el OCR y el PDF no caben en el ciclo de petición; hace falta cola (segunda tabla o worker con `asyncio`) y eso ya está abierto en [[Coherencia]] (I5).
- **Pruebas:** `pytest` + una base PostgreSQL real en CI (no SQLite: el modelo usa `JSONB`, `UUID`, particiones y `INET`).
- **Pendiente de confirmar:** versión de Python en el servidor del Colegio, política de actualizaciones y si el despliegue es contenedor o servicio. Lo decide @Kevin.
- Fuera de alcance: elección de ORM (se propone SQL explícito), herramienta de CI y observabilidad.
