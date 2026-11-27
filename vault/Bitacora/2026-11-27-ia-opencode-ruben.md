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

## Siguiente

- Ejecutar las pruebas de BD cuando haya PostgreSQL (`DATABASE_TEST_URL`) y probar el flujo completo de #55.
- Queda fuera de esta rama: purga de ficheros cifrados al borrar, escritura del original dentro de la transacción y tope de memoria del ZIP a 100 PDFs.

## Bloqueos / preguntas

- Sin Docker ni PostgreSQL en este equipo, las pruebas `*_bd` no se han podido ejecutar.
