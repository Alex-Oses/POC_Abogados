# 2026-11-27 · @ia-opencode-ruben

## Hecho

Arreglados, sobre la rama `fix/backend-cola-reglas` (sale de `feat/backend-documentos`, PR #55), los fallos detectados al revisar su backend:

- **A-01**: borrar o cancelar durante el OCR ya no resucita el documento. El worker bloquea la fila en cada página, solo cierra si sigue en `ocr_procesando` y el camino de error tampoco lo devuelve a `pendiente`.
- **Acción por defecto** de anonimizar y reabrir: vuelve a `censurar` (rgpd-considerations.md); `borrar` queda como opción explícita.
- **Semáforo de calidad**: editar texto o formato ya no lo pone en verde; solo `validada: true` lo hace.
- **Reintento de OCR**: nuevo `POST /documents/{id}/retry` para un OCR fallido o cancelado (A-02).
- **ZIP**: cada documento se exporta y confirma en su propia transacción; la ruta queda en el contrato (`docs/api/endpoints.md`).
- **Solapes de anotaciones** en el PDF final: se recortan al tramo libre, nunca se descarta la anotación (A-09).
- **SharePoint**: dos usuarios con el mismo nombre ya no se adivinan (se avisa y no se sube); `DOCUMENTO_SUBIDO` va con actor sistema y la carpeta en `detalle`.
- **Consultas con nombre** para las dos SQL que estaban en `services/documents.py`; `pool.abrir` ya no usa atributos privados; el NDJSON cierra con evento si el documento se borra.

Pruebas: `test_export.py` nuevo (solapes del marcado, sin BD) y casos de reintento, borrado durante OCR y semáforo en `test_cola_ocr_bd.py`. `ruff` limpio; `pytest` 22 pasan / 12 saltan (las de BD, sin PostgreSQL aquí).

- **Docker**: `backend/Dockerfile` (contexto: raíz del repo, porque el backend sirve `templates/` y `static/`) y `.dockerignore`. Python 3.12-slim, usuario sin privilegios, modelo `es_core_news_md` instalado (sin él Presidio no ve personas), `/app/storage` como volumen y `HEALTHCHECK` contra `/health`. Un solo worker: la cola de OCR es por proceso.

## Revisión de la estructura y PR que sustituye a #55

- **Estructura**: revisado `backend/app` contra [[Estructura del backend (Python)]]. Coincide en lo que importa (síncrono, transacción por petición, `services/` separado, auth que solo identifica, SQL con nombre). Las diferencias están documentadas en la sección 6 de ese documento; ninguna toca el contrato.
- **Dos cambios aplicados** de esa tabla: `anonymize.py` y `export.py` vuelven a ser routers propios (mismos paths y permisos, `documents.py` de 396 a ~250 líneas) y se retira `app/integrations/`, vacía desde que el OCR pasó a `services/`.
- **Rama nueva que sustituye a #55**: `main` ya integrado en `fix/backend-cola-reglas` (`a81692f`). El backend de `main` es subconjunto del de #55, así que el merge se resolvió tomando esta rama en todos los conflictos; del tablero se conservó la fecha de entrega del lunes 30/11 que traía `main`. `ruff` limpio y 22 pruebas en verde tras el merge.
- **PR #56** contra `main`: https://github.com/Alex-Oses/POC_Abogados/pull/56. Comentario en #55 avisando de que queda sustituido, para que lo cierre cuando las pruebas de BD estén en verde.
- **Docker**: `backend/Dockerfile` y `.dockerignore` (ver nota anterior).

## Siguiente

- Ejecutar las pruebas de BD cuando haya PostgreSQL (`DATABASE_TEST_URL`) y probar el flujo completo de #55.
- Queda fuera de esta rama: purga de ficheros cifrados al borrar, escritura del original dentro de la transacción y tope de memoria del ZIP a 100 PDFs.

## Bloqueos / preguntas

- Sin Docker ni PostgreSQL en este equipo, las pruebas `*_bd` no se han podido ejecutar.
